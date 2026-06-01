import csv
import os
import sys  # ⭐ Agregado para importar auth
from fastapi import APIRouter, HTTPException, Depends  # ⭐ Agregado Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from coneeccion import ejecutar_consulta
# ⭐ Importar autenticación
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from auth.security import requerir_autenticacion, requerir_admin, TokenData

router = APIRouter()

FILE_NAME = "data/inventario_v2.csv"
# ⭐ HEADERS actualizados con nuevos campos
HEADERS = ["id_producto", "cantidad", "ubicacion", "ultima_actualizacion", "stock_minimo"]

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

# ⭐ Modelos V2 con campos adicionales
class InventarioV2(BaseModel):
    id_producto: int
    cantidad: int
    created_at: str
    updated_at: str

class InventarioRegistroV2(BaseModel):
    id_producto: int
    cantidad: int = Field(..., ge=1)

class InventarioUpdateV2(BaseModel):
    cantidad: int = Field(..., ge=1)
def leer_inventario():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ==================== ENDPOINTS V2 CON AUTH ====================
# ⭐ GET - Requiere autenticación
# GET /inventario
@router.get("/inventario", response_model=List[InventarioV2], tags=["v2 - Consultas"])
def obtener_inventario_v2():
    resultados = ejecutar_consulta("SELECT * FROM rz_inventario_listar();")
    for r in resultados:
        if hasattr(r['created_at'], 'strftime'):
            r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            r['updated_at'] = r['updated_at'].strftime("%Y-%m-%d %H:%M:%S")
    return resultados if resultados else []

# GET /inventario/{id_producto}
@router.get("/inventario/{id_producto}", response_model=InventarioV2, tags=["v2 - Consultas"])
def obtener_inventario_por_id_v2(id_producto: int):
    resultados = ejecutar_consulta("SELECT * FROM rz_inventario_porid(%s);", (id_producto,))
    if not resultados:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    r = resultados[0]
    if hasattr(r['created_at'], 'strftime'):
        r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        r['updated_at'] = r['updated_at'].strftime("%Y-%m-%d %H:%M:%S")
    return r

# POST /inventario
@router.post("/inventario", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)], status_code=201)
def registrar_inventario_v2(nuevo: InventarioRegistroV2, token_data: TokenData = Depends(requerir_admin)):
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_inventario_agregar(%s, %s);",
        (nuevo.id_producto, nuevo.cantidad)
    )
    if not resultados:
        raise HTTPException(status_code=500, detail="Error en BD")
    return {"mensaje": resultados[0]["mensaje"], "id_producto": resultados[0]["id_producto"], "status": "success"}

# PATCH /inventario/{id_producto}
@router.patch("/inventario/{id_producto}", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)])
def actualizar_inventario_v2(id_producto: int, update: InventarioUpdateV2, token_data: TokenData = Depends(requerir_admin)):
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_inventario_actualizar(%s, %s);",
        (id_producto, update.cantidad)
    )
    if not resultados:
        return {"mensaje": "Actualizado", "status": "success"}
    if resultados[0]["mensaje"] == "Registro no encontrado":
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}

# DELETE /inventario/{id_producto}
@router.delete("/inventario/{id_producto}", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)])
def eliminar_inventario_v2(id_producto: int, token_data: TokenData = Depends(requerir_admin)):
    resultados = ejecutar_consulta("SELECT * FROM rz_inventario_eliminar(%s);", (id_producto,))
    if not resultados:
        return {"mensaje": "Eliminado", "status": "success"}
    if resultados[0]["mensaje"] == "Registro no encontrado":
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}