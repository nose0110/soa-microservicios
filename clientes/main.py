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
    requerir_autenticacion,
    requerir_admin,
    Token,
    TokenData,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {"message": "Servicio activo", "web_ui": "/static/index.html", "docs": "/docs"}

app = FastAPI(
    title="Departamento de Clientes",
    description="Servicio de Clientes con versionado y autenticación JWT\n\n" \
    "Ejecutar en puerto **8000** y asegurarse de que los servicios de Pedidos (8002) y Productos (8001) estén activos.",
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
        200: {
            "description": "Token generado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "username": "admin",
                        "rol": "administrador"
                    }
                }
            }
        },
        400: {
            "description": "Credenciales incorrectas"
        }
    }
)
# ⭐ CORRECCIÓN CLAVE: form_data: (con dos puntos y nombre completo)
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
    """**Endpoint raíz con información de versiones disponibles.**"""
    return {
        "servicio": "Departamento de Clientes",
        "versiones": {
            "v1": "/v1/clientes",
            "v2": "/v2/clientes"
        },
        "auth": "/auth/token",
        "documentacion": "/docs",
        "usuarios_prueba": {
            "admin": "admin123",
            "usuario": "usuario123"
        }
    }

# ⭐ Importar routers de cada versión
from serv_clientes_v1 import router as router_v1
from serv_clientes_v2 import router as router_v2

# ⭐ Incluir routers con prefijo de versión
app.include_router(router_v1, prefix="/v1", tags=["Versión 1"])
app.include_router(router_v2, prefix="/v2", tags=["Versión 2"])