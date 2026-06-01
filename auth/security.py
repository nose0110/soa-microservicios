from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# ==================== CONFIGURACIÓN ====================
SECRET_KEY = "soa_tecnm_2024_clave_secreta_super_segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# ==================== MODELOS ====================
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    rol: str

class TokenData(BaseModel):
    username: Optional[str] = None
    rol: Optional[str] = None

# ==================== USUARIOS (Comparación directa - PARA PRUEBAS) ====================
USUARIOS_DB = {
    "admin": {
        "username": "admin",
        "password": "admin123",
        "rol": "administrador"
    },
    "usuario": {
        "username": "usuario", 
        "password": "usuario123",
        "rol": "usuario"
    }
}

# ==================== FUNCIONES ====================
def crear_token_acceso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT con los datos proporcionados."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def autenticar_usuario(username: str, password: str):
    """Autentica un usuario con username y password."""
    usuario = USUARIOS_DB.get(username)
    if not usuario:
        return None
    if usuario["password"] != password:
        return None
    return usuario

async def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Obtiene los datos del usuario desde el token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales no válidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        rol: str = payload.get("rol")
        
        if username is None:
            raise credentials_exception
        
        return TokenData(username=username, rol=rol)
    
    except JWTError:
        raise credentials_exception

async def requerir_autenticacion(token_data: TokenData = Depends(obtener_usuario_actual)) -> TokenData:
    """Dependencia para proteger endpoints. Requiere autenticación."""
    if token_data.username is None:
        raise HTTPException(
            status_code=401, 
            detail="Usuario no autenticado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return token_data

async def requerir_admin(token_data: TokenData = Depends(obtener_usuario_actual)) -> TokenData:
    """Dependencia para endpoints que solo administradores pueden usar."""
    if token_data.username is None:
        raise HTTPException(
            status_code=401, 
            detail="Usuario no autenticado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if token_data.rol != "administrador":
        raise HTTPException(
            status_code=403, 
            detail="Permiso denegado. Se requiere rol de administrador"
        )
    
    return token_data