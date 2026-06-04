from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles  # ⭐ AGREGADO: Para servir el index.html
from datetime import timedelta
import sys
import os
import requests

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

app = FastAPI(
    title="Departamento de Productos",
    description="Servicio de Productos con versionado y autenticación JWT",
    version="3.0.0",
    contact={"name": "Arturo Barajas, Profesor de SOA - TecNM Querétaro"}
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⭐ AGREGADO: Montar carpeta 'static' para la interfaz web (index.html)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ⭐ ENDPOINT DE LOGIN
@app.get("/health", tags=["Health"])
def health_check():
    """Verificar que el servicio está conectado a la BD"""
    try:
        from coneeccion import ejecutar_consulta
        resultado = ejecutar_consulta("SELECT current_database(), current_user;")
        return {
            "status": "✅ ok",
            "service": "productos",
            "database": resultado[0]['current_database'],
            "user": resultado[0]['current_user'],
            "message": "Conectado a PostgreSQL en Render"
        }
    except Exception as e:
        return {"status": "❌ error", "detail": str(e)}, 500
@app.post("/auth/token", response_model=Token, tags=["Autenticación"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
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

# ⭐ Endpoint raíz
@app.get("/", tags=["Root"])
def root():
    return {
        "servicio": "Departamento de Productos",
        "version": "3.0.0 (V1, V2, V3 Proxy)",
        "versiones": {
            "v1": "/v1/productos (Python Básico)",
            "v2": "/v2/productos (Python Extendido + BD)",
            "v3": "/v3/productos (Node.js - Proxy)"
        },
        "web_ui": "/static/index.html",  # ⭐ AGREGADO: Enlace a la interfaz
        "auth": "/auth/token",
        "docs": "/docs",
        "usuarios_prueba": {"admin": "admin123", "usuario": "usuario123"}
    }

# ⭐ Importar routers Python
from serv_productos_v1 import router as router_v1
from serv_productos_v2 import router as router_v2

app.include_router(router_v1, prefix="/v1", tags=["V1 - Python"])
app.include_router(router_v2, prefix="/v2", tags=["V2 - Python"])

# ==================== ENDPOINTS V3 (Node.js) - PROXY ====================
# ⭐ NOTA: Si no tienes el servicio Node.js corriendo, esto devolverá 503.
# ¡Esto es PERFECTO para tu video demo de "Manejo de Errores 503"!

NODE_BASE_URL = "http://localhost:8011/v3"

def _get_token_from_request(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    return auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""

@app.get("/v3/productos", tags=["V3 - Node.js"], dependencies=[Depends(requerir_autenticacion)])
async def v3_get_productos(request: Request, token_data: TokenData = Depends(requerir_autenticacion)):
    try:
        token = _get_token_from_request(request)
        resp = requests.get(f"{NODE_BASE_URL}/productos", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Servicio Node.js no disponible (Error 503 intencional para demo)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxy: {str(e)}")

@app.get("/v3/productos/{id_producto}", tags=["V3 - Node.js"], dependencies=[Depends(requerir_autenticacion)])
async def v3_get_producto(id_producto: int, request: Request, token_data: TokenData = Depends(requerir_autenticacion)):
    try:
        token = _get_token_from_request(request)
        resp = requests.get(f"{NODE_BASE_URL}/productos/{id_producto}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Servicio Node.js no disponible")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxy: {str(e)}")

@app.post("/v3/productos", tags=["V3 - Node.js"], dependencies=[Depends(requerir_admin)], status_code=201)
async def v3_post_producto(request: Request, nuevo: dict, token_data: TokenData = Depends(requerir_admin)):
    try:
        token = _get_token_from_request(request)
        resp = requests.post(f"{NODE_BASE_URL}/productos", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=nuevo, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Servicio Node.js no disponible")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxy: {str(e)}")

@app.patch("/v3/productos/{id_producto}", tags=["V3 - Node.js"], dependencies=[Depends(requerir_admin)])
async def v3_patch_producto(id_producto: int, request: Request, update: dict, token_data: TokenData = Depends(requerir_admin)):
    try:
        token = _get_token_from_request(request)
        resp = requests.patch(f"{NODE_BASE_URL}/productos/{id_producto}", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=update, timeout=5)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Servicio Node.js no disponible")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxy: {str(e)}")

@app.delete("/v3/productos/{id_producto}", tags=["V3 - Node.js"], dependencies=[Depends(requerir_admin)])
async def v3_delete_producto(id_producto: int, request: Request, token_data: TokenData = Depends(requerir_admin)):
    try:
        token = _get_token_from_request(request)
        resp = requests.delete(f"{NODE_BASE_URL}/productos/{id_producto}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Servicio Node.js no disponible")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxy: {str(e)}")