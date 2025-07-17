import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.model import glbm_wilayah, glbm_wilayah_cakupan, glbm_samsat
from app.db.database import SessionLocal

# Inisialisasi session
db = SessionLocal()

# ===== DATA WILAYAH =====
wilayah_nama = "DKI & Serang"
cakupan_nama = "DKI:B"

# Cek atau buat wilayah
wilayah = db.query(glbm_wilayah).filter_by(nama_wilayah=wilayah_nama).first()
if not wilayah:
    wilayah = glbm_wilayah(nama_wilayah=wilayah_nama)
    db.add(wilayah)
    db.commit()
    db.refresh(wilayah)
    print(f"✓ Tambah wilayah: {wilayah_nama}")

# Cek atau buat cakupan
cakupan = db.query(glbm_wilayah_cakupan).filter_by(
    nama_wilayah=cakupan_nama,
    wilayah_id=wilayah.id
).first()
if not cakupan:
    cakupan = glbm_wilayah_cakupan(
        nama_wilayah=cakupan_nama,
        wilayah_id=wilayah.id
    )
    db.add(cakupan)
    db.commit()
    db.refresh(cakupan)
    print(f"✓ Tambah cakupan: {cakupan_nama}")

# ===== DATA SAMSAT =====
data_samsat = [
    {"kode_samsat": "UTR", "nama_samsat": "Utara"},
    {"kode_samsat": "PST", "nama_samsat": "PUSAT"},
    {"kode_samsat": "TMR", "nama_samsat": "TIMUR"},
    {"kode_samsat": "BRT", "nama_samsat": "BARAT"},
    {"kode_samsat": "SLT", "nama_samsat": "SELATAN"},
]

for data in data_samsat:
    existing = db.query(glbm_samsat).filter_by(kode_samsat=data["kode_samsat"]).first()
    if not existing:
        samsat = glbm_samsat(
            kode_samsat=data["kode_samsat"],
            nama_samsat=data["nama_samsat"],
            wilayah_id=wilayah.id,
            wilayah_cakupan_id=cakupan.id
        )
        db.add(samsat)
        print(f"✓ Tambah samsat: {data['kode_samsat']} - {data['nama_samsat']}")

db.commit()
db.close()
print("✅ Selesai menambahkan Samsat DKI.")
