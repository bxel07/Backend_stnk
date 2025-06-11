from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class STNKData(Base):
    __tablename__ = "stnk_data"
    
    id = Column(Integer, primary_key=True, index=True)
    file = Column(String, nullable=True)
    nomor_rangka = Column(String, nullable=True)
    corrected = Column(Boolean, default=False)  # Add this line
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    corrections = relationship(
        "STNKFieldCorrection",
        back_populates="stnk_data",
        cascade="all, delete-orphan"
    )


class STNKFieldCorrection(Base):
    __tablename__ = "stnk_field_corrections"
    
    id = Column(Integer, primary_key=True, index=True)
    stnk_data_id = Column(Integer, ForeignKey("stnk_data.id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    corrected_at = Column(DateTime, default=datetime.utcnow)
    
    stnk_data = relationship("STNKData", back_populates="corrections")