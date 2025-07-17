import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text

# Import engine dari database
from app.db.database import engine

def reset_stnk_data():
    try:
        with Session(engine) as session:
            # Menghapus semua data dari stnk_data dan tabel terkait yang berelasi foreign key
            session.execute(text("TRUNCATE TABLE stnk_data CASCADE"))
            session.commit()
            print("✅ Semua data dalam tabel stnk_data dan relasinya berhasil di-reset (TRUNCATE + CASCADE)")
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat reset data: {e}")

if __name__ == "__main__":
    reset_stnk_data()
