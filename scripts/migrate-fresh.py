import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from app.db.database import Base, engine
from sqlalchemy import text

# Import semua model agar metadata lengkap
from app.db.model import (
    User, stpm_orlap, Role,
    STNKData, STNKFieldCorrection,
    glbm_wilayah_cakupan, glbm_wilayah,
    glbm_samsat, otorirasi_samsat, Detail_otorirasi_samsat,glbm_brand, glbm_pt,
)

def reset_database():
    with engine.connect() as conn:
        # Nonaktifkan constraint check dan drop semua tabel dengan CASCADE
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    reset_database()
