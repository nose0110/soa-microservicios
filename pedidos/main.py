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
    title="Departamento de Pedidos",
    description="Servicio de Pedidos (Orquestador) con Base de Datos, RabbitMQ y Autenticación JWT",
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

# ⭐ AGREGADO: Crear carpeta static y montar los archivos (index.html)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ⭐ ENDPOINT DE LOGIN
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
        "version": "3.0.0 (Orquestador con BD + Auth)",
        "web_ui": "/static/index.html",  # ⭐ AGREGADO: Enlace a tu interfaz gráfica
        "auth": "/auth/token",
        "docs": "/docs",
        "health": "/health",
        "usuarios_prueba": {
            "admin": "admin123",
            "usuario": "usuario123"
        },
        "servicios_dependientes": {
            "clientes": "http://localhost:8000/v2/clientes",
            "productos": "http://localhost:8011/v3/productos",
            "inventario": "http://localhost:8003/v2/inventario"
        }
    }

# ⭐ AGREGADO: Endpoint para verificar que la BD está conectada (clave para la demo)
@app.get("/health", tags=["Health"])
def health_check():
    try:
        from coneeccion import ejecutar_consulta
        resultado = ejecutar_consulta("SELECT current_database(), current_user;")
        return {
            "status": "✅ ok",
            "service": "pedidos",
            "database": resultado[0]['current_database'],
            "message": "Conectado a PostgreSQL en Render"
        }
    except Exception as e:
        return {"status": "❌ error", "detail": str(e)}, 500

# ⭐ Importar routers (Mantenemos tu estructura original intacta)
from serv_pedidos_v2 import router as router_v2  

# Nota: Si NO tienes un archivo llamado 'serv_pedidos_v3.py', deja comentada la siguiente línea:
# from serv_pedidos_v3 import router as router_v3

# ⭐ Incluir routers con prefijos de versión
#app.include_router(router_v2, prefix="/v2", tags=["Pedidos v2 (Orquestador BD)"])
app.include_router(router_v3, prefix="/v3", tags=["Versión 3 - BD"])