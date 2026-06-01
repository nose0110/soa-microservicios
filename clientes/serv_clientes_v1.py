import csv
import os
from fastapi import APIRouter, HTTPException ,Depends # ⭐ Cambiado
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional

router = APIRouter()  # ⭐ Cambiado de app = FastAPI()

FILE_NAME = "clientes.csv"
HEADERS = ["id_cliente", "nombre", "correo", "direccion", "telefono"]


if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

class Cliente(BaseModel):
    id_cliente: int = Field(..., example=101, description="ID numérico único")  # type: ignore
    nombre: str = Field(..., min_length=3, example="Juan Pérez")  # type: ignore
    correo: EmailStr = Field(..., example="juan@ejemplo.com")  # type: ignore
    direccion: str = Field(..., example="Calle 123")  # type: ignore
    telefono: str = Field(..., example="555-1234")  # type: ignore

class ClienteRegistro(BaseModel):
    nombre: str = Field(..., min_length=3, example="Juan Pérez")  # type: ignore
    correo: EmailStr = Field(..., example="juan@ejemplo.com")  # type: ignore
    direccion: str = Field(..., example="Calle 123")  # type: ignore
    telefono: str = Field(..., example="555-1234")  # type: ignore

class ClienteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, example="Juan Pérez")  # type: ignore
    correo: Optional[EmailStr] = Field(None, example="juan@ejemplo.com")  # type: ignore
    direccion: Optional[str] = Field(None, example="Calle 123")  # type: ignore
    telefono: Optional[str] = Field(None, example="555-1234")  # type: ignore

def leer_clientes():
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@router.get(  # ⭐ Cambiado @app por @router
    "/clientes",
    response_model=List[Cliente],
    tags=["v1 - Consultas"],  # ⭐ Tag actualizado
    summary="Obtener lista de clientes (V1)",
    status_code=200,
    responses={
        200: {
            "description": "Lista de clientes obtenida exitosamente",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id_cliente": 101,
                            "nombre": "Juan Pérez",
                            "correo": "juan@ejemplo.com",
                            "direccion": "Calle 123",
                            "telefono": "555-1234"
                        }
                    ]
                }
            }
        }
    }
)
def obtener_clientes():
    return leer_clientes()

@router.get(  # ⭐ Cambiado @app por @router
    "/clientes/{id_cliente}",
    response_model=Cliente,
    tags=["v1 - Consultas"],
    summary="Obtener cliente por ID (V1)",
    status_code=200,
    responses={
        200: {"description": "Cliente obtenido exitosamente"},
        404: {"description": "Cliente no encontrado"}
    }
)
def obtener_cliente_por_id(id_cliente: int):
    clientes = leer_clientes()
    cliente = next((c for c in clientes if int(c['id_cliente']) == id_cliente), None)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

@router.post(  # ⭐ Cambiado @app por @router
    "/clientes",
    tags=["v1 - Operaciones"],
    summary="Registrar nuevo cliente (V1)",
    status_code=201,
    responses={
        201: {"description": "Cliente registrado exitosamente"},
        422: {"description": "Datos inválidos"}
    }
)
def registrar_cliente(nuevo: ClienteRegistro):
    clientes = leer_clientes()
    if clientes:
        siguiente_id = max(int(c['id_cliente']) for c in clientes) + 1
    else:
        siguiente_id = 1
    
    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([siguiente_id, nuevo.nombre, nuevo.correo, nuevo.direccion, nuevo.telefono])
    return {"mensaje": "Cliente registrado (V1)", "id_cliente": siguiente_id, "status": "success"}

@router.delete(  # ⭐ Cambiado @app por @router
    "/clientes/{id_cliente}",
    tags=["v1 - Operaciones"],
    summary="Eliminar cliente (V1)",
    status_code=200,
    responses={
        200: {"description": "Cliente eliminado exitosamente"},
        404: {"description": "Cliente no encontrado"}
    }
)
def eliminar_cliente(id_cliente: int):
    clientes = leer_clientes()
    cliente = next((c for c in clientes if int(c['id_cliente']) == id_cliente), None)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    clientes.remove(cliente)
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(clientes)
    
    return {"mensaje": "Cliente eliminado (V1)", "status": "success"}

@router.patch(  # ⭐ Cambiado @app por @router
    "/clientes/{id_cliente}",
    tags=["v1 - Operaciones"],
    summary="Actualizar cliente parcialmente (V1)",
    status_code=200,
    responses={
        200: {"description": "Cliente actualizado exitosamente"},
        404: {"description": "Cliente no encontrado"},
        422: {"description": "Datos inválidos"}
    }
)
def actualizar_cliente_parcial(id_cliente: int, update: ClienteUpdate):
    clientes = leer_clientes()
    cliente = next((c for c in clientes if int(c['id_cliente']) == id_cliente), None)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    if update.nombre is not None:
        cliente['nombre'] = update.nombre
    if update.correo is not None:
        cliente['correo'] = update.correo
    if update.direccion is not None:
        cliente['direccion'] = update.direccion
    if update.telefono is not None:
        cliente['telefono'] = update.telefono
    
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(clientes)
    
    return {"mensaje": "Cliente actualizado (V1)", "status": "success"}