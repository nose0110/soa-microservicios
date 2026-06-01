const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 8011;
const SECRET_KEY = 'soa_tecnm_2024_clave_secreta_super_segura';
const CSV_FILE = path.join(__dirname, 'data', 'productos_v3.csv');

app.use(cors());
app.use(express.json());

// Usuarios
const USUARIOS = {
  admin: { username: 'admin', password: 'admin123', rol: 'administrador' },
  usuario: { username: 'usuario', password: 'usuario123', rol: 'usuario' }
};

// Crear CSV si no existe
if (!fs.existsSync(CSV_FILE)) {
  fs.mkdirSync(path.dirname(CSV_FILE), { recursive: true });
  fs.writeFileSync(CSV_FILE, 'id_producto,descripcion,precio,categoria,stock_minimo\n');
}

// Leer CSV
function leerProductos() {
  const content = fs.readFileSync(CSV_FILE, 'utf8');
  const lines = content.trim().split('\n').slice(1);
  return lines.map(line => {
    const [id, descripcion, precio, categoria, stock_minimo] = line.split(',');
    return { 
      id_producto: parseInt(id), 
      descripcion, 
      precio: parseFloat(precio), 
      categoria, 
      stock_minimo: parseInt(stock_minimo) 
    };
  });
}

// Guardar CSV
function guardarProductos(productos) {
  let csv = 'id_producto,descripcion,precio,categoria,stock_minimo\n';
  productos.forEach(p => {
    csv += `${p.id_producto},${p.descripcion},${p.precio},${p.categoria},${p.stock_minimo}\n`;
  });
  fs.writeFileSync(CSV_FILE, csv);
}

// Autenticación
function verificarToken(req, res, next) {
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) {
    return res.status(401).json({ detail: 'Not authenticated' });
  }
  
  try {
    const token = auth.split(' ')[1];
    const payload = jwt.verify(token, SECRET_KEY);
    req.user = payload;
    next();
  } catch (e) {
    res.status(401).json({ detail: 'Invalid token' });
  }
}

function requerirAdmin(req, res, next) {
  if (req.user.rol !== 'administrador') {
    return res.status(403).json({ detail: 'Se requiere admin' });
  }
  next();
}

// ==================== ENDPOINTS ====================

app.post('/auth/token', (req, res) => {
  const { username, password } = req.body;
  const user = USUARIOS[username];
  
  if (!user || user.password !== password) {
    return res.status(400).json({ detail: 'Credenciales incorrectas' });
  }
  
  const token = jwt.sign({ sub: user.username, rol: user.rol }, SECRET_KEY, { expiresIn: '30m' });
  res.json({ access_token: token, token_type: 'bearer', username: user.username, rol: user.rol });
});

app.get('/', (req, res) => {
  res.json({ servicio: 'Productos V3 (Node.js)', version: '3.0.0', lenguaje: 'Node.js' });
});

app.get('/v3/productos', (req, res) => {
  res.json(leerProductos());
});
app.get('/v3/productos/:id', (req, res) => {
  const productos = leerProductos();
  const prod = productos.find(p => p.id_producto === parseInt(req.params.id));
  if (!prod) return res.status(404).json({ detail: 'No encontrado' });
  res.json(prod);
});
app.post('/v3/productos', verificarToken, requerirAdmin, (req, res) => {
  const productos = leerProductos();
  const nuevoId = productos.length > 0 ? Math.max(...productos.map(p => p.id_producto)) + 1 : 1;
  
  const nuevo = {
    id_producto: nuevoId,
    descripcion: req.body.descripcion,
    precio: req.body.precio,
    categoria: req.body.categoria || 'General',
    stock_minimo: req.body.stock_minimo || 5
  };
  
  productos.push(nuevo);
  guardarProductos(productos);
  
  res.status(201).json({ mensaje: 'Producto registrado (V3 Node.js)', id_producto: nuevoId, status: 'success' });
});

app.patch('/v3/productos/:id', verificarToken, requerirAdmin, (req, res) => {
  const productos = leerProductos();
  const idx = productos.findIndex(p => p.id_producto === parseInt(req.params.id));
  
  if (idx === -1) return res.status(404).json({ detail: 'No encontrado' });
  
  productos[idx] = { ...productos[idx], ...req.body };
  guardarProductos(productos);
  
  res.json({ mensaje: 'Producto actualizado (V3 Node.js)', status: 'success' });
});

app.delete('/v3/productos/:id', verificarToken, requerirAdmin, (req, res) => {
  let productos = leerProductos();
  const idx = productos.findIndex(p => p.id_producto === parseInt(req.params.id));
  
  if (idx === -1) return res.status(404).json({ detail: 'No encontrado' });
  
  productos.splice(idx, 1);
  guardarProductos(productos);
  
  res.json({ mensaje: 'Producto eliminado (V3 Node.js)', status: 'success' });
});

app.listen(PORT, () => {
  console.log(`🚀 Productos V3 (Node.js) corriendo en http://localhost:${PORT}`);
});