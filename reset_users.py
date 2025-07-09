from app.db.database import engine
from app.db.model import User

# Drop dan buat ulang tabel "users" saja
User.__table__.drop(engine)
print("❌ Tabel 'users' di-drop.")

User.__table__.create(engine)
print("✅ Tabel 'users' dibuat ulang.")
