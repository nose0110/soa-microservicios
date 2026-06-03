import os
import sys
from rabbitmq_client import publicar_mensaje, QUEUES
import requests
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from coneeccion import ejecutar_consulta

# ⭐ Importar autenticación
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from auth.security import requerir_autenticacion, requerir_admin, TokenData

router = APIRouter()

# ⭐ URLs de los servicios externos
CLIENTES_URL = os.environ.get("CLIENTES_URL", "http://localhost:8000/v2/clientes")
PRODUCTOS_URL = os.environ.get("PRODUCTOS_URL", "http://localhost:8011/v3/productos")
INVENTARIO_URL = os.environ.get("INVENTARIO_URL", "http://localhost:8003/v2/inventario")
# ==================== MODELOS V3 ====================
class PedidoV2(BaseModel):
    pedido_id: int          # ← Cambiar de 'id_pedido' a 'pedido_id'
    id_cliente: int
    id_producto: int
    cantidad: int
    created_at: str

class PedidoRegistroV2(BaseModel):
    id_cliente: int = Field(..., ge=1)
    id_producto: int = Field(..., ge=1)
    cantidad: int = Field(..., ge=1)

class PedidoUpdateV2(BaseModel):
    cantidad: Optional[int] = Field(None, ge=1)
# ==================== Funciones auxiliares ====================
def validar_cliente(id_cliente: int) -> bool:
    try:
        response = requests.get(f"v2/{CLIENTES_URL}/{id_cliente}", timeout=5)
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

# ==================== ENDPOINTS V3 (Base de Datos) ====================

# GET /pedidos
@router.get(
    "/pedidos",
    response_model=List[PedidoV2],
    tags=["v2 - Consultas"],
    dependencies=[Depends(requerir_autenticacion)]
)
def obtener_pedidos_v2(token_data: TokenData = Depends(requerir_autenticacion)):
    """Obtener todos los pedidos desde BD"""
    resultados = ejecutar_consulta("SELECT * FROM rz_pedidos_listar();")
    
    for r in resultados:
        if hasattr(r['created_at'], 'strftime'):
            r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
    
    return resultados if resultados else []

# GET /pedidos/{id_pedido}
@router.get(
    "/pedidos/{id_pedido}",
    response_model=PedidoV2,
    tags=["v2 - Consultas"],
    dependencies=[Depends(requerir_autenticacion)]
)
def obtener_pedido_v2(id_pedido: int, token_data: TokenData = Depends(requerir_autenticacion)):
    """Obtener pedido por ID desde BD"""
    resultados = ejecutar_consulta("SELECT * FROM rz_pedidos_porid(%s);", (id_pedido,))
    
    if not resultados:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    r = resultados[0]
    if hasattr(r['created_at'], 'strftime'):
        r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
    
    return r

# POST /pedidos
@router.post(
    "/pedidos",
    tags=["v2 - Operaciones"],
    dependencies=[Depends(requerir_autenticacion)],
    status_code=201
)
def registrar_pedido_v2(nuevo: PedidoRegistroV2, token_data: TokenData = Depends(requerir_autenticacion)):
    """Registrar nuevo pedido en BD"""
    
    # Validar cliente
    if not validar_cliente(nuevo.id_cliente):
        raise HTTPException(status_code=400, detail="Cliente no encontrado")
    
    # Validar producto y obtener precio
    producto = validar_producto(nuevo.id_producto)
    if not producto:
        raise HTTPException(status_code=400, detail="Producto no encontrado")
    
    # Validar stock
    if not validar_stock(nuevo.id_producto, nuevo.cantidad):
        raise HTTPException(status_code=400, detail="Stock insuficiente")
    
    # Calcular costo total
    precio_unitario = float(producto.get("precio", 0))
    costo_total = precio_unitario * nuevo.cantidad
    
    # Registrar pedido en BD (SP rz_pedidos_agregar)
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_pedidos_agregar(%s, %s, %s);",
        (nuevo.id_cliente, nuevo.id_producto, nuevo.cantidad)
    )
    
    if not resultados:
        raise HTTPException(status_code=500, detail="Error al registrar pedido")
    
    # Actualizar inventario (restar stock)
    try:
        inv_response = requests.get(f"{INVENTARIO_URL}/{nuevo.id_producto}", timeout=5)
        if inv_response.status_code == 200:
            stock_actual = int(inv_response.json().get("cantidad", 0))
            nuevo_stock = stock_actual - nuevo.cantidad
            requests.patch(
                f"{INVENTARIO_URL}/{nuevo.id_producto}",
                json={"cantidad": nuevo_stock},
                timeout=5
            )
    except:
        pass  # Si falla, el worker puede manejarlo
    
    # Encolar notificación
    publicar_mensaje(QUEUES.get("pedidos", "pedidos.default"), {  # ✅ Usa .get() con fallback
    "pedido_id": resultados[0]["pedido_id"],
    "id_cliente": nuevo.id_cliente,
    "id_producto": nuevo.id_producto,
    "cantidad": nuevo.cantidad
    })
    
    return {
        "mensaje": "Pedido registrado",
        "pedido_id": resultados[0]["pedido_id"],
        "costo_total": costo_total,
        "status": "success"
    }

# PATCH /pedidos/{id_pedido}
@router.patch(
    "/pedidos/{id_pedido}",
    tags=["v2 - Operaciones"],
    dependencies=[Depends(requerir_admin)]
)
def actualizar_pedido_v2(id_pedido: int, update: PedidoUpdateV2, token_data: TokenData = Depends(requerir_admin)):
    """Actualizar pedido en BD"""
    
    # Si se actualiza cantidad, validar stock
    if update.cantidad is not None:
        # Obtener cantidad actual del pedido
        pedido_actual = ejecutar_consulta("SELECT * FROM rz_pedidos_porid(%s);", (id_pedido,))
        if not pedido_actual:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        cantidad_anterior = pedido_actual[0]["cantidad"]
        diferencia = update.cantidad - cantidad_anterior
        
        # Validar stock si aumenta la cantidad
        if diferencia > 0:
            if not validar_stock(pedido_actual[0]["id_producto"], diferencia):
                raise HTTPException(status_code=400, detail="Stock insuficiente")
            
            # Actualizar inventario
            try:
                inv_response = requests.get(f"{INVENTARIO_URL}/{pedido_actual[0]['id_producto']}", timeout=5)
                if inv_response.status_code == 200:
                    stock_actual = int(inv_response.json().get("cantidad", 0))
                    nuevo_stock = stock_actual - diferencia
                    requests.patch(
                        f"{INVENTARIO_URL}/{pedido_actual[0]['id_producto']}",
                        json={"cantidad": nuevo_stock},
                        timeout=5
                    )
            except:
                pass
    
    # Actualizar en BD
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_pedidos_actualizar(%s, %s);",
        (id_pedido, update.cantidad)
    )
    
    if not resultados:
        return {"mensaje": "Pedido actualizado", "status": "success"}
    
    if resultados[0]["mensaje"] == "Pedido no encontrado":
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}

# DELETE /pedidos/{id_pedido}
@router.delete(
    "/pedidos/{id_pedido}",
    tags=["v2 - Operaciones"],
    dependencies=[Depends(requerir_admin)]
)
def eliminar_pedido_v2(id_pedido: int, token_data: TokenData = Depends(requerir_admin)):
    """Eliminar pedido de BD"""
    
    resultados = ejecutar_consulta("SELECT * FROM rz_pedidos_eliminar(%s);", (id_pedido,))
    
    if not resultados:
        return {"mensaje": "Pedido eliminado", "status": "success"}
    
    if resultados[0]["mensaje"] == "Pedido no encontrado":
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}

# GET /pedidos/cliente/{id_cliente}
@router.get(
    "/pedidos/cliente/{id_cliente}",
    response_model=List[PedidoV2],
    tags=["v2 - Consultas"],
    dependencies=[Depends(requerir_autenticacion)]
)
def obtener_pedidos_por_cliente_v2(id_cliente: int, token_data: TokenData = Depends(requerir_autenticacion)):
    """Obtener pedidos de un cliente específico"""
    todos = ejecutar_consulta("SELECT * FROM rz_pedidos_listar();")
    
    filtrados = [p for p in todos if p['id_cliente'] == id_cliente]
    
    for r in filtrados:
        if hasattr(r['created_at'], 'strftime'):
            r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
    
    return filtrados