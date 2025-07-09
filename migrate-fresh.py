from app.db.database import Base, engine

# 🧠 PENTING: import semua model di sini
from app.db.model import User
from app.db.model import stpm_orlap
from app.db.model import Role
from app.db.model import STNKData, STNKFieldCorrection

def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    reset_database()