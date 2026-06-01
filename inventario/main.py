from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles  # ⭐ AGREGADO: Para servir la interfaz web
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
    description="Servicio de Inventario V2 con Autenticación JWT y PostgreSQL\n\n" \
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

# ⭐ AGREGADO: Crear carpeta static y montar los archivos (index.html)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
        "version": "2.0.0 (V2 con Autenticación y BD)",
        "versiones": {
            "v2": "/v2/inventario"
        },
        "web_ui": "/static/index.html",  # ⭐ AGREGADO: Enlace a tu interfaz gráfica
        "auth": "/auth/token",
        "documentacion": "/docs",
        "health": "/health",
        "usuarios_prueba": {
            "admin": "admin123",
            "usuario": "usuario123"
        }
    }

# ⭐ AGREGADO: Endpoint para verificar que la BD está conectada (útil para la demo)
@app.get("/health", tags=["Health"])
def health_check():
    try:
        from coneeccion import ejecutar_consulta
        resultado = ejecutar_consulta("SELECT current_database(), current_user;")
        return {
            "status": "✅ ok",
            "service": "inventario",
            "database": resultado[0]['current_database'],
            "message": "Conectado a PostgreSQL en Render"
        }
    except Exception as e:
        return {"status": "❌ error", "detail": str(e)}, 500

# ⭐ Importar router V2 (tu archivo serv_inventario_v2.py se queda intacto)
from serv_inventario_v2 import router as router_v2

# ⭐ Incluir router con prefijo de versión
app.include_router(router_v2, prefix="/v2", tags=["Versión 2"])