import sys
import os

# Menambahkan folder root ke PYTHONPATH agar bisa import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from app.db.model import master_excel

def reset_master_excel_table():
    try:
        print("Menghapus tabel 'master_excel' jika ada...")
        master_excel.__table__.drop(engine, checkfirst=True)
        print("Tabel berhasil di-drop.")

        print("Membuat ulang tabel 'master_excel'...")
        master_excel.__table__.create(engine, checkfirst=True)
        print("Tabel berhasil dibuat ulang.")
    except Exception as e:
        print("Terjadi kesalahan:", str(e))

if __name__ == "__main__":
    reset_master_excel_table()
