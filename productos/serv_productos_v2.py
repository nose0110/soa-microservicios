import csv
import os
import sys
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from coneeccion import ejecutar_consulta

# ⭐ Importar autenticación
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from auth.security import requerir_autenticacion, requerir_admin, TokenData

router = APIRouter()

FILE_NAME = "data/productos_v2.csv"
HEADERS = ["id_producto", "descripcion", "precio", "categoria", "stock_minimo"]

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)
class ProductoV2(BaseModel):
    id_producto: int
    descripcion: str
    precio: float
    activo: bool
    created_at: str
    updated_at: str

class ProductoRegistroV2(BaseModel):
    descripcion: str
    precio: float = Field(..., ge=0)

class ProductoUpdateV2(BaseModel):
    descripcion: Optional[str] = None
    precio: Optional[float] = Field(None, ge=0)
def leer_productos():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))
# GET /productos
@router.get("/productos", response_model=List[ProductoV2], tags=["v2 - Consultas"])
def obtener_productos_v2():
    resultados = ejecutar_consulta("SELECT * FROM rz_productos_listar();")
    for r in resultados:
        if hasattr(r['created_at'], 'strftime'):
            r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            r['updated_at'] = r['updated_at'].strftime("%Y-%m-%d %H:%M:%S")
    return resultados if resultados else []

# GET /productos/{id_producto}
@router.get("/productos/{id_producto}", response_model=ProductoV2, tags=["v2 - Consultas"])
def obtener_producto_por_id_v2(id_producto: int):
    resultados = ejecutar_consulta("SELECT * FROM rz_productos_porid(%s);", (id_producto,))
    if not resultados:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    r = resultados[0]
    if hasattr(r['created_at'], 'strftime'):
        r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        r['updated_at'] = r['updated_at'].strftime("%Y-%m-%d %H:%M:%S")
    return r

# POST /productos
@router.post("/productos", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)], status_code=201)
def registrar_producto_v2(nuevo: ProductoRegistroV2, token_data: TokenData = Depends(requerir_admin)):
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_productos_agregar(%s, %s);",
        (nuevo.descripcion, nuevo.precio)
    )
    if not resultados:
        raise HTTPException(status_code=500, detail="Error en BD")
    # ⚠️ Nota: el SP regresa 'producto_id' no 'id_producto'
    return {"mensaje": resultados[0]["mensaje"], "id_producto": resultados[0]["producto_id"], "status": "success"}

# PATCH /productos/{id_producto}
@router.patch("/productos/{id_producto}", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)])
def actualizar_producto_v2(id_producto: int, update: ProductoUpdateV2, token_data: TokenData = Depends(requerir_admin)):
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_productos_actualizar(%s, %s, %s);",
        (id_producto, update.descripcion, update.precio)
    )
    if not resultados:
        return {"mensaje": "Actualizado", "status": "success"}
    if resultados[0]["mensaje"] == "Producto no encontrado":
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}

# DELETE /productos/{id_producto}
@router.delete("/productos/{id_producto}", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)])
def eliminar_producto_v2(id_producto: int, token_data: TokenData = Depends(requerir_admin)):
    resultados = ejecutar_consulta("SELECT * FROM rz_productos_eliminar(%s);", (id_producto,))
    if not resultados:
        return {"mensaje": "Eliminado", "status": "success"}
    if resultados[0]["mensaje"] == "Producto no encontrado":
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}