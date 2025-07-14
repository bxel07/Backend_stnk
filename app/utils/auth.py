from jose import JWTError, jwt
from datetime import datetime, timedelta
from enum import Enum
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Konfigurasi JWT
SECRET_KEY = "STNK_RAHASIA"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Buat token
def create_access_token(data: dict):
    to_encode = data.copy()
    
    # Jika role adalah Enum, ubah ke .value agar bisa diserialisasi JSON
    if "role" in to_encode and isinstance(to_encode["role"], Enum):
        to_encode["role"] = to_encode["role"].value

    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Verifikasi token (dipanggil otomatis oleh Depends)
def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Ambil current user dari token
def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak ditemukan",
        )
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kedaluwarsa",
        )
    return payload

# Role-based middleware: hanya izinkan role tertentu
def require_role(*roles: Enum):
    def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses untuk fitur ini",
            )
        return user
    return role_checker
