from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text, Enum,Date
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
    glbm_samsat_id = Column(Integer, ForeignKey("glbm_samsat.id"), nullable=True)
    file = Column(String, nullable=True)
    path = Column(String, nullable=True)
    nomor_rangka = Column(String, nullable=True)
    kode_samsat = Column(String, nullable=True)
    jumlah = Column(Integer, nullable=True)
    nama_pt = Column(String, nullable=True)
    nama_brand = Column(String, nullable=True)
    corrected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ), onupdate=lambda: datetime.now(JAKARTA_TZ), nullable=False)

    corrections = relationship("STNKFieldCorrection", back_populates="stnk_data", cascade="all, delete-orphan")
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
    ORLAP = "orlap"
    CAO = "cao"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(RoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=RoleEnum.USER.value, nullable=False)

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
    otorisasi_samsat = relationship("otorisasi_samsat", back_populates="user", cascade="all, delete-orphan")
    stnk_data = relationship("STNKData", back_populates="user", cascade="all, delete-orphan")

# ========================= Wilayah ==============================

class glbm_wilayah(Base):
    __tablename__ = "glbm_wilayah"

    id = Column(Integer, primary_key=True, index=True)
    nama_wilayah = Column(String, nullable=False)

    samsats = relationship("glbm_samsat", back_populates="wilayah", cascade="all, delete-orphan")
    detail_otorisasi_samsat = relationship("Detail_otorisasi_samsat", back_populates="wilayah", cascade="all, delete-orphan")
    wilayah_cakupan = relationship("glbm_wilayah_cakupan", back_populates="wilayah", cascade="all, delete-orphan")

class glbm_wilayah_cakupan(Base):
    __tablename__ = "glbm_wilayah_cakupan"

    id = Column(Integer, primary_key=True, index=True)
    wilayah_id = Column(Integer, ForeignKey("glbm_wilayah.id"), nullable=False)
    nama_wilayah = Column(String, nullable=False)

    wilayah = relationship("glbm_wilayah", back_populates="wilayah_cakupan")
    samsats = relationship("glbm_samsat", back_populates="wilayah_cakupan")
    detail_otorisasi_samsat = relationship("Detail_otorisasi_samsat", back_populates="detail_wilayah_cakupan")

# ========================= Samsat ==============================

class glbm_samsat(Base):
    __tablename__ = "glbm_samsat"

    id = Column(Integer, primary_key=True, index=True)
    nama_samsat = Column(String, nullable=False)
    kode_samsat = Column(String, nullable=False)
    wilayah_cakupan_id = Column(Integer, ForeignKey("glbm_wilayah_cakupan.id"), nullable=False)
    wilayah_id = Column(Integer, ForeignKey("glbm_wilayah.id"), nullable=False)

    wilayah = relationship("glbm_wilayah", back_populates="samsats")
    wilayah_cakupan = relationship("glbm_wilayah_cakupan", back_populates="samsats")
    detail_otorisasi_samsat = relationship("Detail_otorisasi_samsat", back_populates="glbm_samsat")
    stnk_data = relationship("STNKData", back_populates="glbm_samsat", cascade="all, delete-orphan")

    def as_dict(self):
        return {
            "id": self.id,
            "nama_samsat": self.nama_samsat,
            "kode_samsat": self.kode_samsat,
            "wilayah_cakupan_id": self.wilayah_cakupan_id
        }

# ========================= Detail Otorisasi ==============================

class Detail_otorisasi_samsat(Base):
    __tablename__ = "detail_otorisasi_samsat"

    id = Column(Integer, primary_key=True, index=True)
    glbm_samsat_id = Column(Integer, ForeignKey("glbm_samsat.id"), nullable=False)
    wilayah_cakupan_id = Column(Integer, ForeignKey("glbm_wilayah_cakupan.id"), nullable=False)
    wilayah_id = Column(Integer, ForeignKey("glbm_wilayah.id"), nullable=False)
    glbm_brand_id = Column(Integer, ForeignKey("glbm_brand.id"), nullable=True)
    glbm_pt_id = Column(Integer, ForeignKey("glbm_pt.id"), nullable=True)
    otorisasi_samsat_id = Column(Integer, ForeignKey("otorisasi_samsat.id"), nullable=False)

    wilayah = relationship("glbm_wilayah", back_populates="detail_otorisasi_samsat")
    detail_wilayah_cakupan = relationship("glbm_wilayah_cakupan", back_populates="detail_otorisasi_samsat")
    glbm_samsat = relationship("glbm_samsat", back_populates="detail_otorisasi_samsat")
    otorisasi_samsat = relationship("otorisasi_samsat", back_populates="detail_otorisasi_samsat")
    glbm_brand = relationship("glbm_brand", back_populates="detail_otorisasi_samsat")
    glbm_pt = relationship("glbm_pt", back_populates="detail_otorisasi_samsat")

# ========================= Otorisasi ==============================

class otorisasi_samsat(Base):
    __tablename__ = "otorisasi_samsat"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(JAKARTA_TZ), onupdate=lambda: datetime.now(JAKARTA_TZ), nullable=False)

    detail_otorisasi_samsat = relationship("Detail_otorisasi_samsat", back_populates="otorisasi_samsat")
    user = relationship("User", back_populates="otorisasi_samsat")

# ========================= Brand & PT ==============================

class glbm_brand(Base):
    __tablename__ = "glbm_brand"

    id = Column(Integer, primary_key=True, index=True)
    nama_brand = Column(String, nullable=False)
    kode_brand = Column(String, nullable=False)

    detail_otorisasi_samsat = relationship("Detail_otorisasi_samsat", back_populates="glbm_brand")

class glbm_pt(Base):
    __tablename__ = "glbm_pt"

    id = Column(Integer, primary_key=True, index=True)
    nama_pt = Column(String, nullable=False)
    kode_pt = Column(String, nullable=False)

    detail_otorisasi_samsat = relationship("Detail_otorisasi_samsat", back_populates="glbm_pt")

class master_excel(Base):
    __tablename__ = "master_excel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    norangka = Column(String,unique=True)
    nama_stnk = Column(String)
    kode_tipe = Column(String)
    tipe = Column(String)
    kode_model = Column(String)
    model = Column(String)
    merk = Column(String)
    kode_samsat = Column(String)
    samsat = Column(String)
    kode_dealer = Column(String)
    nama_dealer = Column(String)
    kode_group = Column(String)
    group_perusahaan = Column(String)
    tgl_mohon_stnk = Column(Date)
    tgl_simpan = Column(Date)
    nama_pt = Column(String)
    kode_cabang = Column(String)