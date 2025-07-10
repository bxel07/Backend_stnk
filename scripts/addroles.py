import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from app.db.database import SessionLocal
from app.db.model import Role, RoleEnum

# Buat koneksi ke database
db = SessionLocal()

try:
    # Cek apakah data sudah ada (untuk mencegah duplikat)
    existing_roles = db.query(Role).all()
    if existing_roles:
        print("Roles sudah ada di database.")
    else:
        # Tambahkan semua role
        roles = [
            Role(role=RoleEnum.USER),
            Role(role=RoleEnum.CAO),
            Role(role=RoleEnum.ADMIN),
            Role(role=RoleEnum.SUPERADMIN),
        ]
        db.add_all(roles)
        db.commit()
        print("Role berhasil ditambahkan.")
finally:
    db.close()
