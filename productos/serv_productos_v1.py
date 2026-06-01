import csv
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

FILE_NAME = "data/productos_v1.csv"
HEADERS = ["id_producto", "descripcion", "precio"]

# Crear carpeta data si no existe
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class ProductoV1(BaseModel):
    id_producto: int = Field(..., example=1, description="ID del producto")  # type: ignore
    descripcion: str = Field(..., min_length=3, example="Laptop Gamer")  # type: ignore
    precio: float = Field(..., gt=0, example=15000.0)  # type: ignore

class ProductoRegistroV1(BaseModel):
    descripcion: str = Field(..., min_length=3, example="Laptop Gamer")  # type: ignore
    precio: float = Field(..., gt=0, example=15000.0)  # type: ignore

class ProductoUpdateV1(BaseModel):
    descripcion: Optional[str] = Field(None, min_length=3, example="Laptop Gamer")  # type: ignore
    precio: Optional[float] = Field(None, gt=0, example=15000.0)  # type: ignore

def leer_productos():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@router.get(
    "/productos",
    response_model=List[ProductoV1],
    tags=["v1 - Consultas"],
    summary="Obtener lista de productos (V1)",
    status_code=200
)
def obtener_productos_v1():
    return leer_productos()

@router.get(
    "/productos/{id_producto}",
    response_model=ProductoV1,
    tags=["v1 - Consultas"],
    summary="Obtener producto por ID (V1)",
    status_code=200,
    responses={
        200: {"description": "Producto obtenido exitosamente"},
        404: {"description": "Producto no encontrado"}
    }
)
def obtener_producto_por_id_v1(id_producto: int):
    productos = leer_productos()
    producto = next((p for p in productos if int(p['id_producto']) == id_producto), None)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@router.post(
    "/productos",
    tags=["v1 - Operaciones"],
    summary="Registrar nuevo producto (V1)",
    status_code=201,
    responses={
        201: {"description": "Producto registrado exitosamente"},
        422: {"description": "Datos inválidos"}
    }
)
def registrar_producto_v1(nuevo: ProductoRegistroV1):
    productos = leer_productos()
    
    if productos:
        siguiente_id = max(int(p['id_producto']) for p in productos) + 1
    else:
        siguiente_id = 1
    
    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([siguiente_id, nuevo.descripcion, nuevo.precio])
    
    return {"mensaje": "Producto registrado (V1)", "id_producto": siguiente_id, "status": "success"}

@router.delete(
    "/productos/{id_producto}",
    tags=["v1 - Operaciones"],
    summary="Eliminar producto (V1)",
    status_code=200
)
def eliminar_producto_v1(id_producto: int):
    productos = leer_productos()
    producto = next((p for p in productos if int(p['id_producto']) == id_producto), None)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    productos.remove(producto)
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(productos)
    
    return {"mensaje": "Producto eliminado (V1)", "status": "success"}

@router.patch(
    "/productos/{id_producto}",
    tags=["v1 - Operaciones"],
    summary="Actualizar producto (V1)",
    status_code=200
)
def actualizar_producto_v1(id_producto: int, update: ProductoUpdateV1):
    productos = leer_productos()
    producto = next((p for p in productos if int(p['id_producto']) == id_producto), None)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    if update.descripcion is not None:
        producto['descripcion'] = update.descripcion
    if update.precio is not None:
        producto['precio'] = update.precio
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(productos)
    
    return {"mensaje": "Producto actualizado (V1)", "status": "success"}