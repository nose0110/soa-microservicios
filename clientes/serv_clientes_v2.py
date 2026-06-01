
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
import csv
import os
import sys
sys.path.append(r"C:\Users\zaidy\Downloads\soa\completo 1")

from coneeccion import ejecutar_consulta, ejecutar_comando
# ⭐ Importar autenticación
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from auth.security import requerir_autenticacion, requerir_admin, TokenData

router = APIRouter()

FILE_NAME = "data/clientes_v2.csv"
HEADERS = ["id_cliente", "nombre", "correo", "direccion", "telefono", "activo"]

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class ClienteV2(BaseModel):
    id_cliente: int = Field(..., example=1)
    nombre: str = Field(..., min_length=3)
    correo: EmailStr = Field(...)
    direccion: str = Field(...)
    telefono: str = Field(...)
    activo: bool = Field(...)

class ClienteRegistroV2(BaseModel):
    nombre: str = Field(..., min_length=3)
    correo: EmailStr = Field(...)
    direccion: str = Field(...)
    telefono: str = Field(...)
    activo: bool = Field(default=True)

class ClienteUpdateV2(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3)
    correo: Optional[EmailStr] = Field(None)
    direccion: Optional[str] = Field(None)
    telefono: Optional[str] = Field(None)
    activo: Optional[bool] = Field(None)

def leer_clientes():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ⭐ GET - SIN auth (público para consultas)
@router.get("/clientes", response_model=List[ClienteV2], tags=["v2 - Consultas"])
def obtener_clientes_v2():
    """SP: rz_clientes_listar"""
    resultados = ejecutar_consulta("SELECT * FROM rz_clientes_listar();")
    
    # ✅ Asegurar que siempre sea una lista
    if resultados is None:
        return []
    
    return resultados


@router.get("/clientes/{id_cliente}", response_model=ClienteV2, tags=["v2 - Consultas"])
def obtener_cliente_por_id_v2(id_cliente: int):
    """SP: rz_clientes_porid"""
    resultados = ejecutar_consulta("SELECT * FROM rz_clientes_porid(%s);", (id_cliente,))
    
    if not resultados:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente = resultados[0]
    
    if cliente is None or not isinstance(cliente, dict):
        raise HTTPException(status_code=500, detail="Error: formato de respuesta inválido")
    
    if 'fecha_registro' in cliente and hasattr(cliente['fecha_registro'], 'strftime'):
        cliente['fecha_registro'] = cliente['fecha_registro'].strftime("%Y-%m-%d %H:%M:%S")
    
    return cliente
@router.post("/clientes", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)], status_code=201)
def registrar_cliente_v2(nuevo: ClienteRegistroV2, token_data: TokenData = Depends(requerir_admin)):
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_clientes_agregar(%s, %s, %s, %s);",
        (nuevo.nombre, nuevo.correo, nuevo.direccion or "", nuevo.telefono or "")
    )
    
    if not resultados:
        raise HTTPException(status_code=500, detail="Error: sin respuesta de la BD")
    
    if resultados[0]["id_cliente"] == -1:
        raise HTTPException(status_code=409, detail=resultados[0]["mensaje"])
    
    return {
        "mensaje": resultados[0]["mensaje"], 
        "id_cliente": resultados[0]["id_cliente"], 
        "status": "success"
    }
    
@router.patch("/clientes/{id_cliente}", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)])
def actualizar_cliente_v2(id_cliente: int, update: ClienteUpdateV2, token_data: TokenData = Depends(requerir_admin)):
    """SP: rz_clientes_actualizar"""
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_clientes_actualizar(%s, %s, %s, %s, %s);",
        (id_cliente, update.nombre, update.correo, update.direccion, update.telefono)
    )
    
    # ✅ Validar que haya resultados antes de acceder a [0]
    if not resultados:
        # Si se actualizó pero no hubo respuesta, asumimos éxito
        return {"mensaje": "Cliente actualizado", "status": "success"}
    
    if resultados[0]["mensaje"] == "Cliente no encontrado":
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}

# ⭐ DELETE - Solo administradores
@router.delete("/clientes/{id_cliente}", tags=["v2 - Operaciones"], dependencies=[Depends(requerir_admin)])
def eliminar_cliente_v2(id_cliente: int, token_data: TokenData = Depends(requerir_admin)):
    """SP: rz_clientes_eliminar"""
    resultados = ejecutar_consulta(
        "SELECT * FROM rz_clientes_eliminar(%s);",
        (id_cliente,)
    )
    
    # ✅ Validar que haya resultados antes de acceder a [0]
    if not resultados:
        # Si se borró pero no hubo respuesta, asumimos éxito
        return {"mensaje": "Cliente eliminado", "status": "success"}
    
    if resultados[0]["mensaje"] == "Cliente no encontrado":
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    return {"mensaje": resultados[0]["mensaje"], "status": "success"}