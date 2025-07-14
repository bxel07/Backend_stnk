import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import Base, engine
from sqlalchemy.orm import Session
from sqlalchemy import delete

# Import model STNKData
from app.db.model import STNKData

def reset_stnk_data():
    with Session(engine) as session:
        session.execute(delete(STNKData))  # Menghapus semua data STNK
        session.commit()
        print("✅ Data STNK berhasil di-reset (dihapus semua)")

if __name__ == "__main__":
    reset_stnk_data()
