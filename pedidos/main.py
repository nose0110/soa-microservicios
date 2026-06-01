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
    title="Departamento de Pedidos",
    description="Servicio de Pedidos V3 con Base de Datos y Autenticación JWT\n\n" \
    "Ejecutar en puerto **8002** y asegurarse de que los servicios de Clientes (8000), Productos (8011) e Inventario (8003) estén activos.",
    version="3.0.0",
    contact={
        "name": "Arturo Barajas, Profesor de SOA - TecNM Querétaro",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⭐ ENDPOINT DE LOGIN (igual que antes)
@app.post("/auth/token", response_model=Token, tags=["Autenticación"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """**Obtiene un token de acceso JWT.**"""
    usuario = await autenticar_usuario(form_data.username, form_data.password)
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = crear_token_acceso(
        data={"sub": usuario["username"], "rol": usuario["rol"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": usuario["username"],
        "rol": usuario["rol"]
    }

# ⭐ Endpoint raíz actualizado
@app.get("/", tags=["Root"])
def root():
    return {
        "servicio": "Departamento de Pedidos",
        "version": "3.0.0 (Base de Datos + Auth)",
        "versiones": {
            "v2": "/v2/pedidos (CSV + RabbitMQ)",
            "v3": "/v3/pedidos (PostgreSQL + Auth)"  # ← Nuevo
        },
        "auth": "/auth/token",
        "docs": "/docs",
        "usuarios_prueba": {
            "admin": "admin123",
            "usuario": "usuario123"
        },
        "servicios_dependientes": {
            "clientes": "http://localhost:8000/v2/clientes",
            "productos": "http://localhost:8011/v3/productos",  # ← Puerto actualizado
            "inventario": "http://localhost:8003/v2/inventario"
        }
    }

# ⭐ Importar routers (V2 y V3)
from serv_pedidos_v2 import router as router_v2  # ← Tu archivo actual
from serv_pedidos_v3 import router as router_v3  # ← Nuevo archivo para V3

# ⭐ Incluir routers con prefijos de versión
app.include_router(router_v2, prefix="/v2", tags=["Versión 2 - CSV"])
app.include_router(router_v3, prefix="/v3", tags=["Versión 3 - BD"])  # ← Nuevo