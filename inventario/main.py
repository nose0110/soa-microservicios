from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import sys
import os

# ⭐ Agregar la carpeta auth al path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from auth.security import (
    crear_token_acceso,
    autenticar_usuario,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(
    title="Departamento de Inventario",
    description="Servicio de Inventario V2 con Autenticación JWT\n\n" \
    "Ejecutar en puerto **8003** y asegurarse de que el servicio de Productos (8001) esté activo.",
    version="2.0.0",
    contact={
        "name": "Arturo Barajas, Profesor de SOA - TecNM Querétaro",
    }
)

# CORS para comunicación entre computadoras
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⭐ ENDPOINT DE LOGIN
@app.post(
    "/auth/token",
    response_model=Token,
    tags=["Autenticación"],
    summary="Obtener token de acceso",
    status_code=200,
    responses={
        200: {"description": "Token generado exitosamente"},
        400: {"description": "Credenciales incorrectas"}
    }
)
# ⭐ CORRECCIÓN CLAVE: form_ (con dos puntos y nombre completo)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """**Obtiene un token de acceso JWT.**"""
    usuario = await autenticar_usuario(form_data.username, form_data.password)
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # ⭐ Acceder como diccionario ["key"]
    access_token = crear_token_acceso(
        data={"sub": usuario["username"], "rol": usuario["rol"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": usuario["username"],
        "rol": usuario["rol"]
    }

# ⭐ Endpoint público para verificar estado
@app.get(
    "/",
    tags=["Root"],
    summary="Información del servicio",
    status_code=200
)
def root():
    """**Endpoint raíz con información del servicio.**"""
    return {
        "servicio": "Departamento de Inventario",
        "version": "2.0.0 (V2 con Autenticación)",
        "versiones": {
            "v2": "/v2/inventario"
        },
        "auth": "/auth/token",
        "documentacion": "/docs",
        "usuarios_prueba": {
            "admin": "admin123",
            "usuario": "usuario123"
        }
    }

# ⭐ Importar router V2
from serv_inventario_v2 import router as router_v2

# ⭐ Incluir router con prefijo de versión
app.include_router(router_v2, prefix="/v2", tags=["Versión 2"])