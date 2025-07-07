from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, timezone
from app.db.database import Base

# UTC+7 Timezone (WIB)
JAKARTA_TZ = timezone(timedelta(hours=7))

# Model ini mencakup informasi dasar seperti nomor rangka, jumlah, dan status koreksi
class STNKData(Base):
    __tablename__ = "stnk_data"
    
    id = Column(Integer, primary_key=True, index=True)
    file = Column(String, nullable=True)
    path = Column(String, nullable=True)
    nomor_rangka = Column(String, nullable=True)
    jumlah = Column(Integer, nullable=True)
    corrected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ),
                        onupdate=lambda: datetime.now(JAKARTA_TZ), nullable=False)
    
    corrections = relationship(
        "STNKFieldCorrection",
        back_populates="stnk_data",
        cascade="all, delete-orphan"
    )

# Model ini mencakup nama field yang dikoreksi, nilai asli, dan nilai kore
class STNKFieldCorrection(Base):
    __tablename__ = "stnk_field_corrections"
    
    id = Column(Integer, primary_key=True, index=True)
    stnk_data_id = Column(Integer, ForeignKey("stnk_data.id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    corrected_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ))

    stnk_data = relationship("STNKData", back_populates="corrections")
