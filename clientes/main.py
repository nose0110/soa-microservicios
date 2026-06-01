from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
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

# ==========================================
# 1. PRIMERO: CREAR LA INSTANCIA DE FASTAPI
# ==========================================
app = FastAPI(
    title="Departamento de Clientes",
    description="Servicio de Clientes con Autenticación JWT y PostgreSQL",
    version="2.0.0"
)

# ==========================================
# 2. SEGUNDO: MIDDLEWARE (CORS)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. TERCERO: MONTAR ARCHIVOS ESTÁTICOS (Ahora 'app' ya existe)
# ==========================================
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================================
# 4. CUARTO: ENDPOINTS
# ==========================================
@app.post("/auth/token", response_model=Token, tags=["Autenticación"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Obtiene un token de acceso JWT."""
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

@app.get("/", tags=["Root"])
def root():
    return {
        "servicio": "Departamento de Clientes",
        "version": "2.0.0",
        "web_ui": "/static/index.html",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Verificar que el servicio está conectado a la BD"""
    try:
        from coneeccion import ejecutar_consulta
        resultado = ejecutar_consulta("SELECT current_database(), current_user;")
        return {
            "status": "✅ ok",
            "service": "clientes",
            "database": resultado[0]['current_database'],
            "user": resultado[0]['current_user'],
            "message": "Conectado a PostgreSQL en Render"
        }
    except Exception as e:
        return {"status": "❌ error", "detail": str(e)}, 500

# ==========================================
# 5. QUINTO: IMPORTAR Y USAR EL ROUTER
# ==========================================
from serv_clientes_v2 import router as router_v2  # Asegúrate que este archivo exista

app.include_router(router_v2, prefix="/v2", tags=["Clientes v2"])