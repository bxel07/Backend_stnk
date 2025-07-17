import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.db.database import Base, engine

# Tambahkan direktori project ke sys.path agar modul 'app' bisa diimpor

# Impor semua model agar metadata terdaftar dan create_all tidak melewatkan tabel
from app.db.model import (
    User, stpm_orlap, Role,
    STNKData, STNKFieldCorrection,
    glbm_wilayah_cakupan, glbm_wilayah,
    glbm_samsat, otorisasi_samsat, Detail_otorisasi_samsat,
    glbm_brand, glbm_pt, master_excel
)

def reset_database():
    # Gunakan begin() untuk menjalankan semua perintah dalam 1 transaksi
    with engine.begin() as conn:
        print("🚨 Menghapus skema public...")
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        print("✅ Skema public dibuat ulang.")

    # Buat ulang seluruh tabel berdasarkan metadata model
    print("⚙️ Membuat ulang seluruh tabel...")
    Base.metadata.create_all(bind=engine)
    print("✅ Semua tabel berhasil dibuat.")

if __name__ == "__main__":
    reset_database()
