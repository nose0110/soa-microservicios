import csv
import os
from rabbitmq_client import publicar_mensaje, QUEUES
import sys  # ⭐ Agregado para importar auth
import requests
from fastapi import APIRouter, HTTPException, Depends  # ⭐ Agregado Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from coneeccion import ejecutar_consulta
# ⭐ Importar autenticación
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from auth.security import requerir_autenticacion, requerir_admin, TokenData

router = APIRouter()

# ⭐ URLs de los servicios externos (V2)
CLIENTES_URL = "http://localhost:8000/v2/clientes"
PRODUCTOS_URL = "http://localhost:8011/v3/productos"
INVENTARIO_URL = "http://localhost:8003/v2/inventario"

FILE_NAME = "data/pedidos_v2.csv"
# ⭐ HEADERS actualizados con nuevos campos
HEADERS = ["id_pedido", "id_cliente", "id_producto", "cantidad", "costo_total", "estado", "fecha_pedido", "direccion_entrega", "notas"]

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

# ⭐ Modelos V2 con campos adicionales
class PedidoV2(BaseModel):
    id_pedido: int = Field(..., example=1, description="ID único del pedido")
    id_cliente: int = Field(..., example=101, description="ID del cliente")
    id_producto: int = Field(..., example=1, description="ID del producto")
    cantidad: int = Field(..., gt=0, example=2, description="Cantidad solicitada")
    costo_total: float = Field(..., gt=0, example=30000.0, description="Costo total")
    estado: str = Field(..., example="completado", description="Estado del pedido")
    fecha_pedido: str = Field(..., example="2024-01-15 10:30:00", description="Fecha y hora del pedido")
    direccion_entrega: str = Field(..., example="Calle Entrega 456", description="Dirección de entrega")
    notas: Optional[str] = Field(None, example="Entregar en recepción", description="Notas adicionales")

class PedidoRegistroV2(BaseModel):
    id_cliente: int = Field(..., example=101, description="ID del cliente")
    id_producto: int = Field(..., example=1, description="ID del producto")
    cantidad: int = Field(..., gt=0, example=2, description="Cantidad solicitada")
    direccion_entrega: str = Field(..., example="Calle Entrega 456", description="Dirección de entrega")
    notas: Optional[str] = Field(None, example="Entregar en recepción", description="Notas adicionales")

class PedidoUpdateV2(BaseModel):
    estado: Optional[str] = Field(None, example="cancelado", description="Nuevo estado")
    cantidad: Optional[int] = Field(None, gt=0, example=3, description="Nueva cantidad")
    direccion_entrega: Optional[str] = Field(None, example="Nueva dirección", description="Actualizar dirección")
    notas: Optional[str] = Field(None, example="Actualizar notas", description="Actualizar notas")

def leer_pedidos():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validar_cliente(id_cliente: int) -> bool:
    try:
        response = requests.get(f"{CLIENTES_URL}/{id_cliente}", timeout=5)
        return response.status_code == 200
    except:
        return False

def validar_producto(id_producto: int) -> dict:
    try:
        response = requests.get(f"{PRODUCTOS_URL}/{id_producto}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def validar_stock(id_producto: int, cantidad_requerida: int) -> bool:
    try:
        response = requests.get(f"{INVENTARIO_URL}/{id_producto}", timeout=5)
        if response.status_code == 200:
            inventario = response.json()
            return int(inventario.get("cantidad", 0)) >= cantidad_requerida
        return False
    except:
        return False

def actualizar_stock(id_producto: int, cantidad_restante: int) -> bool:
    try:
        response = requests.patch(
            f"{INVENTARIO_URL}/{id_producto}",
            json={"cantidad": cantidad_restante},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

# ==================== ENDPOINTS V2 CON AUTH ====================
@router.get(
    "/pedidos",
    response_model=List[PedidoV2],
    tags=["v2 - Consultas"],
    dependencies=[Depends(requerir_autenticacion)]
)
def obtener_pedidos_v2(token_data: TokenData = Depends(requerir_autenticacion)):
    """**Versión 2 - Base de datos**"""
    resultados = ejecutar_consulta("SELECT * FROM rz_pedidos_listar_v3();")
    
    # Convertir timestamps a string
    for r in resultados:
        if hasattr(r['fecha_pedido'], 'strftime'):
            r['fecha_pedido'] = r['fecha_pedido'].strftime("%Y-%m-%d %H:%M:%S")
        # Asegurar que los campos opcionales no sean None
        r['notas'] = r['notas'] or ""
        r['direccion_entrega'] = r['direccion_entrega'] or ""
    
    return resultados
    
@router.get(
    "/pedidos/{id_pedido}",
    response_model=PedidoV2,
    tags=["v2 - Consultas"],
    summary="Obtener pedido por ID (V2)",
    status_code=200,
    responses={
        200: {"description": "Pedido obtenido exitosamente"},
        404: {"description": "Pedido no encontrado"}
    },
    dependencies=[Depends(requerir_autenticacion)]  # ⭐ Requiere auth
)
def obtener_pedido_v2(id_pedido: int, token_data: TokenData = Depends(requerir_autenticacion)):  # ⭐ Parámetro token
    """**Versión 2 - Obtener pedido con campos extendidos.**"""
    pedidos = leer_pedidos()
    pedido = next((p for p in pedidos if int(p['id_pedido']) == id_pedido), None)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido

# ⭐ POST - Requiere autenticación (cualquier usuario puede crear pedidos)
@router.post(
    "/pedidos",
    tags=["v2 - Operaciones"],
    summary="Registrar nuevo pedido (V2)",
    status_code=201,
    responses={
        201: {"description": "Pedido registrado o encolado"},
        400: {"description": "Datos inválidos"},
        422: {"description": "Datos inválidos"}
    },
    dependencies=[Depends(requerir_autenticacion)]
)
def registrar_pedido_v2(nuevo: PedidoRegistroV2, token_data: TokenData = Depends(requerir_autenticacion)):
    """**Versión 2 - Registro con cola RabbitMQ para resiliencia.**"""
    
    pedidos = leer_pedidos()
    siguiente_id = (max(int(p['id_pedido']) for p in pedidos) + 1) if pedidos else 1
    
    # Preparar mensaje para cola
    mensaje_validacion = {
        "pedido_id": siguiente_id,
        "id_cliente": nuevo.id_cliente,
        "id_producto": nuevo.id_producto,
        "cantidad": nuevo.cantidad,
        "direccion_entrega": nuevo.direccion_entrega,
        "notas": nuevo.notas or "",
        "timestamp": datetime.now().isoformat()
    }
    
    # 🔄 Estrategia: Intentar validación sincrónica primero
    # Si falla, encolar para procesamiento asíncrono
    
    try:
        # Intentar validar cliente directamente
        if not validar_cliente(nuevo.id_cliente):
            # Si falla, encolar para reintentar después
            publicar_mensaje(QUEUES["clientes"], mensaje_validacion)
            return {
                "mensaje": "Pedido encolado - validación de cliente pendiente",
                "id_pedido": siguiente_id,
                "status": "queued",
                "cola": QUEUES["clientes"]
            }
        
        # Validar producto
        producto = validar_producto(nuevo.id_producto)
        if not producto:
            publicar_mensaje(QUEUES["productos"], mensaje_validacion)
            return {
                "mensaje": "Pedido encolado - validación de producto pendiente",
                "id_pedido": siguiente_id,
                "status": "queued",
                "cola": QUEUES["productos"]
            }
        
        # Validar stock
        if not validar_stock(nuevo.id_producto, nuevo.cantidad):
            publicar_mensaje(QUEUES["inventario"], mensaje_validacion)
            return {
                "mensaje": "Pedido encolado - validación de stock pendiente",
                "id_pedido": siguiente_id,
                "status": "queued",
                "cola": QUEUES["inventario"]
            }
        
        # ✅ Todas las validaciones pasaron - procesar pedido normalmente
        costo_total = float(producto.get("precio", 0)) * nuevo.cantidad
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Actualizar stock
        try:
            response_stock = requests.get(f"{INVENTARIO_URL}/{nuevo.id_producto}", timeout=5)
            stock_actual = int(response_stock.json().get("cantidad", 0))
            nuevo_stock = stock_actual - nuevo.cantidad
            actualizar_stock(nuevo.id_producto, nuevo_stock)
        except:
            pass  # Si falla, el worker lo hará después
        
        # Guardar pedido
        with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                siguiente_id,
                nuevo.id_cliente,
                nuevo.id_producto,
                nuevo.cantidad,
                costo_total,
                "pendiente",  # Estado inicial
                fecha_actual,
                nuevo.direccion_entrega,
                nuevo.notas or ""
            ])
        
        # Encolar actualización de stock para el worker (opcional, para consistencia)
        publicar_mensaje("pedidos.actualizar_stock", {
            "pedido_id": siguiente_id,
            "id_producto": nuevo.id_producto,
            "cantidad": nuevo.cantidad
        })
        
        return {
            "mensaje": "Pedido registrado (V2)",
            "id_pedido": siguiente_id,
            "costo_total": costo_total,
            "status": "success"
        }
        
    except Exception as e:
        # Si hay error inesperado, encolar todo el pedido
        publicar_mensaje("pedidos.procesamiento_fallido", {
            **mensaje_validacion,
            "error": str(e)
        })
        return {
            "mensaje": "Pedido encolado por error inesperado",
            "id_pedido": siguiente_id,
            "status": "queued",
            "error": str(e)
        }
# ⭐ DELETE - Solo administradores
@router.delete(
    "/pedidos/{id_pedido}",
    tags=["v2 - Operaciones"],
    summary="Eliminar pedido (V2)",
    status_code=200,
    dependencies=[Depends(requerir_admin)]  # ⭐ Solo administradores
)
def eliminar_pedido_v2(id_pedido: int, token_data: TokenData = Depends(requerir_admin)):  # ⭐ Parámetro token
    """**Versión 2 - Eliminar pedido.**"""
    pedidos = leer_pedidos()
    pedido = next((p for p in pedidos if int(p['id_pedido']) == id_pedido), None)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    pedidos.remove(pedido)
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(pedidos)
    
    return {"mensaje": "Pedido eliminado (V2)", "status": "success"}

# ⭐ PATCH - Solo administradores
@router.patch(
    "/pedidos/{id_pedido}",
    tags=["v2 - Operaciones"],
    summary="Actualizar pedido (V2)",
    status_code=200,
    dependencies=[Depends(requerir_admin)]  # ⭐ Solo administradores
)
def actualizar_pedido_v2(id_pedido: int, update: PedidoUpdateV2, token_data: TokenData = Depends(requerir_admin)):  # ⭐ Parámetro token
    """**Versión 2 - Actualización con campos adicionales.**"""
    pedidos = leer_pedidos()
    pedido = next((p for p in pedidos if int(p['id_pedido']) == id_pedido), None)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    if update.estado is not None:
        pedido['estado'] = update.estado
    
    if update.cantidad is not None:
        if not validar_stock(pedido['id_producto'], update.cantidad):
            raise HTTPException(status_code=404, detail="Stock insuficiente para la nueva cantidad")
        pedido['cantidad'] = update.cantidad
        producto = validar_producto(pedido['id_producto'])
        if producto:
            pedido['costo_total'] = float(producto.get("precio", 0)) * update.cantidad
    
    if update.direccion_entrega is not None:
        pedido['direccion_entrega'] = update.direccion_entrega
    
    if update.notas is not None:
        pedido['notas'] = update.notas
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(pedidos)
    
    return {"mensaje": "Pedido actualizado (V2)", "status": "success"}

# ⭐ GET por cliente - Requiere autenticación
@router.get(
    "/pedidos/cliente/{id_cliente}",
    response_model=List[PedidoV2],
    tags=["v2 - Consultas"],
    summary="Obtener pedidos por cliente (V2)",
    status_code=200,
    dependencies=[Depends(requerir_autenticacion)]  # ⭐ Requiere auth
)
def obtener_pedidos_por_cliente_v2(id_cliente: int, token_data: TokenData = Depends(requerir_autenticacion)):  # ⭐ Parámetro token
    """**Versión 2 - Pedidos de un cliente con campos extendidos.**"""
    pedidos = leer_pedidos()
    return [p for p in pedidos if int(p['id_cliente']) == id_cliente]