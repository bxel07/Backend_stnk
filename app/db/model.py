from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, timezone
from app.db.database import Base
import enum

# Waktu Jakarta (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))

# ========================= STNK ==============================

class STNKData(Base):
    __tablename__ = "stnk_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    glbm_samsat_id = Column(Integer, ForeignKey("glbm_samsat.id"), nullable=False)
    file = Column(String, nullable=True)
    path = Column(String, nullable=True)
    nomor_rangka = Column(String, nullable=True)
    kode_samsat = Column(String, nullable=True)
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
    user = relationship("User", back_populates="stnk_data")
    glbm_samsat = relationship("glbm_samsat", back_populates="stnk_data")

class STNKFieldCorrection(Base):
    __tablename__ = "stnk_field_corrections"
    
    id = Column(Integer, primary_key=True, index=True)
    stnk_data_id = Column(Integer, ForeignKey("stnk_data.id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    corrected_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ))

    stnk_data = relationship("STNKData", back_populates="corrections")

# ========================= Role ==============================

class RoleEnum(enum.Enum):
    USER = "user"
    CAO = "cao"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(
        Enum(RoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=RoleEnum.USER.value,
        nullable=False
    )

    users = relationship("User", back_populates="role")

# ========================= User ==============================

class stpm_orlap(Base):
    __tablename__ = "stpm_orlap"

    id = Column(Integer, primary_key=True, index=True)
    nama_lengkap = Column(String, nullable=False)
    nomor_telepon = Column(String, nullable=False)

    user = relationship("User", back_populates="stpm_orlap")

class User(Base):
    __tablename__ = "users"
 
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    gmail = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    stpm_orlap_id = Column(Integer, ForeignKey("stpm_orlap.id"), nullable=True)

    role = relationship("Role", back_populates="users")
    stpm_orlap = relationship("stpm_orlap", back_populates="user", uselist=False)
    otorirasi_samsat = relationship("otorirasi_samsat", back_populates="user", cascade="all, delete-orphan")
    stnk_data = relationship("STNKData", back_populates="user", cascade="all, delete-orphan")

# ========================= Wilayah ==============================

class glbm_wilayah(Base):
    __tablename__ = "glbm_wilayah"

    id = Column(Integer, primary_key=True, index=True)
    nama_wilayah = Column(String, nullable=False)

    wilayah_cakupan = relationship("glbm_wilayah_cakupan", back_populates="wilayah", cascade="all, delete-orphan")

class glbm_wilayah_cakupan(Base):
    __tablename__ = "glbm_wilayah_cakupan"

    id = Column(Integer, primary_key=True, index=True)
    wilayah_id = Column(Integer, ForeignKey("glbm_wilayah.id"), nullable=False)
    nama_wilayah = Column(String, nullable=False)

    wilayah = relationship("glbm_wilayah", back_populates="wilayah_cakupan")
    samsats = relationship("glbm_samsat", back_populates="wilayah_cakupan")
    detail_otorirasi_samsat = relationship("Detail_otorirasi_samsat", back_populates="detail_wilayah_cakupan")


# ========================= Samsat ==============================

class glbm_samsat(Base):
    __tablename__ = "glbm_samsat"

    id = Column(Integer, primary_key=True, index=True)
    nama_samsat = Column(String, nullable=False)
    kode_samsat = Column(String, nullable=False)
    wilayah_cakupan_id = Column(Integer, ForeignKey("glbm_wilayah_cakupan.id"), nullable=False)
    wilayah_cakupan = relationship("glbm_wilayah_cakupan", back_populates="samsats")
    detail_otorirasi_samsat = relationship("Detail_otorirasi_samsat", back_populates="glbm_samsat")
    stnk_data = relationship("STNKData", back_populates="glbm_samsat", cascade="all, delete-orphan")

    def as_dict(self):
        return {
            "id": self.id,
            "nama_samsat": self.nama_samsat,
            "kode_samsat": self.kode_samsat,
            "wilayah_cakupan_id": self.wilayah_cakupan_id
        }


class Detail_otorirasi_samsat(Base):
    __tablename__ = "detail_otorirasi_samsat"

    id = Column(Integer, primary_key=True, index=True)
    glbm_samsat_id = Column(Integer, ForeignKey("glbm_samsat.id"), nullable=False)
    wilayah_cakupan_id = Column(Integer, ForeignKey("glbm_wilayah_cakupan.id"), nullable=False)

    detail_wilayah_cakupan = relationship("glbm_wilayah_cakupan", back_populates="detail_otorirasi_samsat")
    otorirasi_samsat = relationship("otorirasi_samsat", back_populates="detail_otorirasi_samsat")
    glbm_samsat = relationship("glbm_samsat", back_populates="detail_otorirasi_samsat")


# ========================= Otorisasi ==============================

class otorirasi_samsat(Base):
    __tablename__ = "otorirasi_samsat"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    detail_otorirasi_samsat_id = Column(Integer, ForeignKey("detail_otorirasi_samsat.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ), onupdate=lambda: datetime.now(JAKARTA_TZ), nullable=False)

    detail_otorirasi_samsat = relationship("Detail_otorirasi_samsat", back_populates="otorirasi_samsat")
    user = relationship("User", back_populates="otorirasi_samsat")

