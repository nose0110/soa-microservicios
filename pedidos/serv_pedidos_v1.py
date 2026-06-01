import csv
import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

# URLs de los servicios externos (V1)
CLIENTES_URL = "http://localhost:8000/v1/clientes"
PRODUCTOS_URL = "http://localhost:8001/v1/productos"
INVENTARIO_URL = "http://localhost:8003/v1/inventario"

FILE_NAME = "data/pedidos_v1.csv"
HEADERS = ["id_pedido", "id_cliente", "id_producto", "cantidad", "costo_total", "estado"]

# Crear carpeta data si no existe
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class PedidoV1(BaseModel):
    id_pedido: int = Field(..., example=1, description="ID único del pedido")  # type: ignore
    id_cliente: int = Field(..., example=101, description="ID del cliente")  # type: ignore
    id_producto: int = Field(..., example=1, description="ID del producto")  # type: ignore
    cantidad: int = Field(..., gt=0, example=2, description="Cantidad solicitada")  # type: ignore
    costo_total: float = Field(..., gt=0, example=30000.0, description="Costo total")  # type: ignore
    estado: str = Field(..., example="completado", description="Estado del pedido")  # type: ignore

class PedidoRegistroV1(BaseModel):
    id_cliente: int = Field(..., example=101, description="ID del cliente")  # type: ignore
    id_producto: int = Field(..., example=1, description="ID del producto")  # type: ignore
    cantidad: int = Field(..., gt=0, example=2, description="Cantidad solicitada")  # type: ignore

class PedidoUpdateV1(BaseModel):
    estado: Optional[str] = Field(None, example="cancelado", description="Nuevo estado")  # type: ignore
    cantidad: Optional[int] = Field(None, gt=0, example=3, description="Nueva cantidad")  # type: ignore

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

# ==================== ENDPOINTS V1 ====================

@router.get(
    "/pedidos",
    response_model=List[PedidoV1],
    tags=["v1 - Consultas"],
    summary="Obtener lista de pedidos (V1)",
    status_code=200
)
def obtener_pedidos_v1():
    return leer_pedidos()

@router.get(
    "/pedidos/{id_pedido}",
    response_model=PedidoV1,
    tags=["v1 - Consultas"],
    summary="Obtener pedido por ID (V1)",
    status_code=200,
    responses={
        200: {"description": "Pedido obtenido exitosamente"},
        404: {"description": "Pedido no encontrado"}
    }
)
def obtener_pedido_v1(id_pedido: int):
    pedidos = leer_pedidos()
    pedido = next((p for p in pedidos if int(p['id_pedido']) == id_pedido), None)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido

@router.post(
    "/pedidos",
    tags=["v1 - Operaciones"],
    summary="Registrar nuevo pedido (V1)",
    status_code=201,
    responses={
        201: {"description": "Pedido registrado exitosamente"},
        400: {"description": "Cliente no encontrado"},
        404: {"description": "Producto o stock insuficiente"},
        422: {"description": "Datos inválidos"}
    }
)
def registrar_pedido_v1(nuevo: PedidoRegistroV1):
    if not validar_cliente(nuevo.id_cliente):
        raise HTTPException(status_code=400, detail="Cliente no encontrado")
    
    producto = validar_producto(nuevo.id_producto)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    if not validar_stock(nuevo.id_producto, nuevo.cantidad):
        raise HTTPException(status_code=404, detail="Stock insuficiente para completar el pedido")
    
    costo_total = float(producto.get("precio", 0)) * nuevo.cantidad
    
    try:
        response_stock = requests.get(f"{INVENTARIO_URL}/{nuevo.id_producto}", timeout=5)
        stock_actual = int(response_stock.json().get("cantidad", 0))
        nuevo_stock = stock_actual - nuevo.cantidad
        actualizar_stock(nuevo.id_producto, nuevo_stock)
    except:
        pass
    
    pedidos = leer_pedidos()
    siguiente_id = (max(int(p['id_pedido']) for p in pedidos) + 1) if pedidos else 1
    
    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([siguiente_id, nuevo.id_cliente, nuevo.id_producto, nuevo.cantidad, costo_total, "completado"])
    
    return {"mensaje": "Pedido registrado (V1)", "id_pedido": siguiente_id, "costo_total": costo_total, "status": "success"}

@router.delete(
    "/pedidos/{id_pedido}",
    tags=["v1 - Operaciones"],
    summary="Eliminar pedido (V1)",
    status_code=200
)
def eliminar_pedido_v1(id_pedido: int):
    pedidos = leer_pedidos()
    pedido = next((p for p in pedidos if int(p['id_pedido']) == id_pedido), None)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    pedidos.remove(pedido)
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(pedidos)
    
    return {"mensaje": "Pedido eliminado (V1)", "status": "success"}

@router.patch(
    "/pedidos/{id_pedido}",
    tags=["v1 - Operaciones"],
    summary="Actualizar pedido (V1)",
    status_code=200
)
def actualizar_pedido_v1(id_pedido: int, update: PedidoUpdateV1):
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
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(pedidos)
    
    return {"mensaje": "Pedido actualizado (V1)", "status": "success"}

@router.get(
    "/pedidos/cliente/{id_cliente}",
    response_model=List[PedidoV1],
    tags=["v1 - Consultas"],
    summary="Obtener pedidos por cliente (V1)",
    status_code=200
)
def obtener_pedidos_por_cliente_v1(id_cliente: int):
    pedidos = leer_pedidos()
    return [p for p in pedidos if int(p['id_cliente']) == id_cliente]