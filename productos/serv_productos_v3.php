<?php
/**
 * Departamento de Productos - Versión PHP
 * Servicio REST con autenticación JWT
 * Puerto: 8011
 */

header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");

// Manejar preflight CORS
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// ==================== CONFIGURACIÓN ====================
define('FILE_NAME', __DIR__ . '/data/productos_v3.csv');
define('SECRET_KEY', 'soa_tecnm_2024_clave_secreta_super_segura');

// ==================== USUARIOS ====================
$USUARIOS_DB = [
    "admin" => [
        "username" => "admin",
        "password" => "admin123",
        "rol" => "administrador"
    ],
    "usuario" => [
        "username" => "usuario",
        "password" => "usuario123",
        "rol" => "usuario"
    ]
];

// ==================== FUNCIONES DE AUTENTICACIÓN ====================
function getBearerToken() {
    $headers = getallheaders();
    if (isset($headers['Authorization'])) {
        $auth = $headers['Authorization'];
        if (strpos($auth, 'Bearer ') === 0) {
            return substr($auth, 7);
        }
    }
    return null;
}

function verificarToken($token) {
    if (!$token) return null;
    
    try {
        $parts = explode('.', $token);
        if (count($parts) !== 3) return null;
        
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+/')), true);
        if (!$payload) return null;
        
        if (isset($payload['exp']) && $payload['exp'] < time()) {
            return null;
        }
        
        return $payload;
    } catch (Exception $e) {
        return null;
    }
}

function requerirAutenticacion() {
    $token = getBearerToken();
    $payload = verificarToken($token);
    
    if (!$payload) {
        http_response_code(401);
        echo json_encode(["detail" => "Not authenticated"]);
        exit();
    }
    
    return $payload;
}

function requerirAdmin() {
    $payload = requerirAutenticacion();
    
    if ($payload['rol'] !== 'administrador') {
        http_response_code(403);
        echo json_encode(["detail" => "Permiso denegado. Se requiere rol de administrador"]);
        exit();
    }
    
    return $payload;
}

function generarToken($username, $rol) {
    $header = base64_encode(json_encode(["alg" => "HS256", "typ" => "JWT"]));
    $payload = base64_encode(json_encode([
        "sub" => $username,
        "rol" => $rol,
        "exp" => time() + (30 * 60)
    ]));
    
    $signature = base64_encode(hash_hmac('sha256', "$header.$payload", SECRET_KEY, true));
    
    return "$header.$payload.$signature";
}

// ==================== FUNCIONES DE CSV ====================
function leerProductos() {
    if (!file_exists(FILE_NAME)) {
        crearArchivoCSV();
        return [];
    }
    
    $productos = [];
    if (($handle = fopen(FILE_NAME, "r")) !== FALSE) {
        $headers = fgetcsv($handle);
        while (($data = fgetcsv($handle)) !== FALSE) {
            $productos[] = array_combine($headers, $data);
        }
        fclose($handle);
    }
    return $productos;
}

function crearArchivoCSV() {
    $dir = dirname(FILE_NAME);
    if (!file_exists($dir)) {
        mkdir($dir, 0777, true);
    }
    
    $file = fopen(FILE_NAME, "w");
    fputcsv($file, ['id_producto', 'descripcion', 'precio', 'categoria', 'stock_minimo']);
    fclose($file);
}

function guardarProducto($producto) {
    $productos = leerProductos();
    $productos[] = $producto;
    
    $file = fopen(FILE_NAME, "w");
    fputcsv($file, ['id_producto', 'descripcion', 'precio', 'categoria', 'stock_minimo']);
    foreach ($productos as $p) {
        fputcsv($file, $p);
    }
    fclose($file);
}

function actualizarProducto($id, $datos) {
    $productos = leerProductos();
    
    foreach ($productos as &$producto) {
        if (intval($producto['id_producto']) === intval($id)) {
            foreach ($datos as $key => $value) {
                if ($value !== null && isset($producto[$key])) {
                    $producto[$key] = $value;
                }
            }
            break;
        }
    }
    
    $file = fopen(FILE_NAME, "w");
    fputcsv($file, ['id_producto', 'descripcion', 'precio', 'categoria', 'stock_minimo']);
    foreach ($productos as $p) {
        fputcsv($file, $p);
    }
    fclose($file);
}

function eliminarProducto($id) {
    $productos = leerProductos();
    $productos = array_filter($productos, function($p) use ($id) {
        return intval($p['id_producto']) !== intval($id);
    });
    
    $file = fopen(FILE_NAME, "w");
    fputcsv($file, ['id_producto', 'descripcion', 'precio', 'categoria', 'stock_minimo']);
    foreach ($productos as $p) {
        fputcsv($file, $p);
    }
    fclose($file);
}

// ==================== ROUTING MANUAL ====================
$method = $_SERVER['REQUEST_METHOD'];
$requestUri = $_SERVER['REQUEST_URI'];

// Eliminar query string si existe
$path = parse_url($requestUri, PHP_URL_PATH);

// ==================== ENDPOINTS ====================

// POST /auth/token - Login
if ($method === 'POST' && $path === '/auth/token') {
    parse_str(file_get_contents("php://input"), $postData);
    
    if (empty($postData) && !empty($_POST)) {
        $postData = $_POST;
    }
    
    $username = $postData['username'] ?? '';
    $password = $postData['password'] ?? '';
    
    if (isset($USUARIOS_DB[$username]) && $USUARIOS_DB[$username]['password'] === $password) {
        $usuario = $USUARIOS_DB[$username];
        $token = generarToken($usuario['username'], $usuario['rol']);
        
        http_response_code(200);
        echo json_encode([
            "access_token" => $token,
            "token_type" => "bearer",
            "username" => $usuario['username'],
            "rol" => $usuario['rol']
        ]);
    } else {
        http_response_code(400);
        echo json_encode(["detail" => "Nombre de usuario o contraseña incorrectos"]);
    }
    exit();
}

// GET / - Root
if ($method === 'GET' && $path === '/') {
    http_response_code(200);
    echo json_encode([
        "servicio" => "Departamento de Productos (PHP)",
        "version" => "3.0.0",
        "lenguaje" => "PHP",
        "auth" => "/auth/token"
    ]);
    exit();
}

// GET /v3/productos - Listar productos
if ($method === 'GET' && $path === '/v3/productos') {
    requerirAutenticacion();
    
    $productos = leerProductos();
    
    foreach ($productos as &$p) {
        $p['id_producto'] = intval($p['id_producto']);
        $p['precio'] = floatval($p['precio']);
        $p['stock_minimo'] = intval($p['stock_minimo']);
    }
    
    http_response_code(200);
    echo json_encode($productos);
    exit();
}

// GET /v3/productos/{id} - Obtener por ID
if ($method === 'GET' && preg_match('#^/v3/productos/(\d+)$#', $path, $matches)) {
    requerirAutenticacion();
    
    $id = intval($matches[1]);
    $productos = leerProductos();
    
    foreach ($productos as $p) {
        if (intval($p['id_producto']) === $id) {
            $p['id_producto'] = intval($p['id_producto']);
            $p['precio'] = floatval($p['precio']);
            $p['stock_minimo'] = intval($p['stock_minimo']);
            
            http_response_code(200);
            echo json_encode($p);
            exit();
        }
    }
    
    http_response_code(404);
    echo json_encode(["detail" => "Producto no encontrado"]);
    exit();
}

// POST /v3/productos - Crear producto
if ($method === 'POST' && $path === '/v3/productos') {
    requerirAdmin();
    
    $input = json_decode(file_get_contents("php://input"), true);
    
    if (!$input) {
        http_response_code(422);
        echo json_encode(["detail" => "Datos inválidos"]);
        exit();
    }
    
    $productos = leerProductos();
    $siguiente_id = !empty($productos) ? max(array_column($productos, 'id_producto')) + 1 : 1;
    
    $nuevoProducto = [
        'id_producto' => $siguiente_id,
        'descripcion' => $input['descripcion'] ?? '',
        'precio' => $input['precio'] ?? 0,
        'categoria' => $input['categoria'] ?? 'General',
        'stock_minimo' => $input['stock_minimo'] ?? 5
    ];
    
    guardarProducto($nuevoProducto);
    
    http_response_code(201);
    echo json_encode([
        "mensaje" => "Producto registrado (V3 PHP)",
        "id_producto" => $siguiente_id,
        "status" => "success"
    ]);
    exit();
}

// PATCH /v3/productos/{id} - Actualizar
if ($method === 'PATCH' && preg_match('#^/v3/productos/(\d+)$#', $path, $matches)) {
    requerirAdmin();
    
    $id = intval($matches[1]);
    $input = json_decode(file_get_contents("php://input"), true);
    
    $productos = leerProductos();
    $encontrado = false;
    
    foreach ($productos as $p) {
        if (intval($p['id_producto']) === $id) {
            $encontrado = true;
            break;
        }
    }
    
    if (!$encontrado) {
        http_response_code(404);
        echo json_encode(["detail" => "Producto no encontrado"]);
        exit();
    }
    
    actualizarProducto($id, $input);
    
    http_response_code(200);
    echo json_encode([
        "mensaje" => "Producto actualizado (V3 PHP)",
        "status" => "success"
    ]);
    exit();
}

// DELETE /v3/productos/{id} - Eliminar
if ($method === 'DELETE' && preg_match('#^/v3/productos/(\d+)$#', $path, $matches)) {
    requerirAdmin();
    
    $id = intval($matches[1]);
    $productos = leerProductos();
    $encontrado = false;
    
    foreach ($productos as $p) {
        if (intval($p['id_producto']) === $id) {
            $encontrado = true;
            break;
        }
    }
    
    if (!$encontrado) {
        http_response_code(404);
        echo json_encode(["detail" => "Producto no encontrado"]);
        exit();
    }
    
    eliminarProducto($id);
    
    http_response_code(200);
    echo json_encode([
        "mensaje" => "Producto eliminado (V3 PHP)",
        "status" => "success"
    ]);
    exit();
}

// Endpoint no encontrado
http_response_code(404);
echo json_encode(["detail" => "Endpoint no encontrado"]);
?>