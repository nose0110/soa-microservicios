import csv
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

FILE_NAME = "data/inventario_v1.csv"
HEADERS = ["id_producto", "cantidad"]

# Crear carpeta data si no existe
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class InventarioV1(BaseModel):
    id_producto: int = Field(..., example=1, description="ID del producto referenciado")  # type: ignore
    cantidad: int = Field(..., ge=0, example=50, description="Cantidad disponible en stock")  # type: ignore

class InventarioRegistroV1(BaseModel):
    id_producto: int = Field(..., example=1, description="ID del producto a registrar")  # type: ignore
    cantidad: int = Field(..., ge=0, example=50, description="Cantidad inicial en stock")  # type: ignore

class InventarioUpdateV1(BaseModel):
    cantidad: Optional[int] = Field(None, ge=0, example=50, description="Nueva cantidad en stock")  # type: ignore

def leer_inventario():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@router.get(
    "/inventario",
    response_model=List[InventarioV1],
    tags=["v1 - Consultas"],
    summary="Obtener lista de inventario (V1)",
    status_code=200
)
def obtener_inventario_v1():
    return leer_inventario()

@router.get(
    "/inventario/{id_producto}",
    response_model=InventarioV1,
    tags=["v1 - Consultas"],
    summary="Obtener inventario por ID (V1)",
    status_code=200,
    responses={
        200: {"description": "Registro obtenido exitosamente"},
        404: {"description": "Producto no encontrado"}
    }
)
def obtener_inventario_por_id_v1(id_producto: int):
    inventario = leer_inventario()
    item = next((i for i in inventario if int(i['id_producto']) == id_producto), None)
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado en inventario")
    return item

@router.post(
    "/inventario",
    tags=["v1 - Operaciones"],
    summary="Registrar producto en inventario (V1)",
    status_code=201,
    responses={
        201: {"description": "Producto registrado exitosamente"},
        409: {"description": "El producto ya existe"},
        422: {"description": "Datos inválidos"}
    }
)
def registrar_inventario_v1(nuevo: InventarioRegistroV1):
    inventario = leer_inventario()
    
    if any(int(item['id_producto']) == nuevo.id_producto for item in inventario):
        raise HTTPException(status_code=409, detail="El producto ya está registrado en el inventario")
    
    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([nuevo.id_producto, nuevo.cantidad])
    return {"mensaje": "Producto registrado en inventario (V1)", "id_producto": nuevo.id_producto, "status": "success"}

@router.delete(
    "/inventario/{id_producto}",
    tags=["v1 - Operaciones"],
    summary="Eliminar producto del inventario (V1)",
    status_code=200
)
def eliminar_inventario_v1(id_producto: int):
    inventario = leer_inventario()
    item = next((i for i in inventario if int(i['id_producto']) == id_producto), None)
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el inventario")
    
    inventario.remove(item)
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(inventario)
    
    return {"mensaje": "Producto eliminado (V1)", "status": "success"}

@router.patch(
    "/inventario/{id_producto}",
    tags=["v1 - Operaciones"],
    summary="Actualizar cantidad (V1)",
    status_code=200
)
def actualizar_inventario_v1(id_producto: int, update: InventarioUpdateV1):
    inventario = leer_inventario()
    item = next((i for i in inventario if int(i['id_producto']) == id_producto), None)
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el inventario")
    
    if update.cantidad is not None:
        item['cantidad'] = update.cantidad
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(inventario)
    
    return {"mensaje": "Cantidad actualizada (V1)", "status": "success"}