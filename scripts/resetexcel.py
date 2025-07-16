import os
import sys

# Tambahkan root project ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from app.db.model import master_excel

def reset_excel_table():
    try:
        # Drop tabel master_excel
        master_excel.__table__.drop(engine)
        print("❌ Tabel 'master_excel' berhasil di-drop.")
    except Exception as e:
        print(f"⚠️ Gagal drop tabel 'master_excel': {str(e)}")

    try:
        # Buat ulang tabel master_excel
        master_excel.__table__.create(engine)
        print("✅ Tabel 'master_excel' berhasil dibuat ulang.")
    except Exception as e:
        print(f"❌ Gagal buat tabel 'master_excel': {str(e)}")

if __name__ == "__main__":
    reset_excel_table()
