# generar_hashes.py
from passlib.context import CryptContext

# Usar PBKDF2 (más compatible que bcrypt)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

print("🔐 Generando hashes con PBKDF2...\n")

# Generar hash para admin
password_admin = "admin123"
hash_admin = pwd_context.hash(password_admin)
print(f"✅ admin123:\n{hash_admin}\n")

# Generar hash para usuario
password_usuario = "usuario123"
hash_usuario = pwd_context.hash(password_usuario)
print(f"✅ usuario123:\n{hash_usuario}\n")

print("📋 Copia estos hashes en auth/security.py")