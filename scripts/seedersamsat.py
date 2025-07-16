import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.model import glbm_wilayah, glbm_wilayah_cakupan, glbm_samsat
from app.db.database import SessionLocal

# Inisialisasi session
db = SessionLocal()

# ===== STEP 1: DATA WILAYAH DAN CAKUPAN =====

wilayah_data = {
    "JAKARTA UTARA": ["JAKARTA UTARA"],
    "BSD": ["BSD"],
    "JAKARTA TIMUR": ["JAKARTA TIMUR"],
    "BALARAJA": ["BALARAJA"],
    "JAKARTA PUSAT": ["JAKARTA PUSAT"],
    "JAKARTA SELATAN": ["JAKARTA SELATAN", "Kebayoran Baru", "Pasar Minggu"],
    "CIPUTAT": ["CIPUTAT"],
    "BEKASI": ["BEKASI"],
    "CILEDUG": ["CILEDUG"],
    "DEPOK": ["DEPOK"],
    "CIKARANG": ["CIKARANG"],
    "JAKARTA BARAT": ["JAKARTA BARAT"],
    "CIKOKOL": ["CIKOKOL"],
    "CINERE": ["CINERE"],
    "BANDUNG": ["Cicendo", "Antapani"],
}

wilayah_objs = {}

# Insert wilayah
for wilayah_name in wilayah_data:
    wilayah = db.query(glbm_wilayah).filter_by(nama_wilayah=wilayah_name).first()
    if not wilayah:
        wilayah = glbm_wilayah(nama_wilayah=wilayah_name)
        db.add(wilayah)
        db.commit()
        db.refresh(wilayah)
        print(f"✓ Tambah wilayah: {wilayah_name}")
    wilayah_objs[wilayah_name] = wilayah

# Insert cakupan
cakupan_objs = {}
for wilayah_name, cakupans in wilayah_data.items():
    wilayah = wilayah_objs[wilayah_name]
    for cakupan_name in cakupans:
        cakupan = db.query(glbm_wilayah_cakupan).filter_by(
            nama_wilayah=cakupan_name, wilayah_id=wilayah.id
        ).first()
        if not cakupan:
            cakupan = glbm_wilayah_cakupan(
                nama_wilayah=cakupan_name,
                wilayah_id=wilayah.id
            )
            db.add(cakupan)
            db.commit()
            db.refresh(cakupan)
            print(f"✓ Tambah cakupan: {cakupan_name} untuk {wilayah_name}")
        cakupan_objs[(cakupan_name, wilayah.id)] = cakupan

# ===== STEP 2: DATA SAMSAT =====

data_samsat = [
    ("UTR", "JAKARTA UTARA"),
    ("BSD", "BSD"),
    ("TMR", "JAKARTA TIMUR"),
    ("BLR", "BALARAJA"),
    ("PST", "JAKARTA PUSAT"),
    ("SLT", "JAKARTA SELATAN"),
    ("CPT", "CIPUTAT"),
    ("BKS", "BEKASI"),
    ("CLG", "CILEDUG"),
    ("DPK", "DEPOK"),
    ("CKR", "CIKARANG"),
    ("BRT", "JAKARTA BARAT"),
    ("CKL", "CIKOKOL"),
    ("CNR", "CINERE"),
]

for kode, nama in data_samsat:
    wilayah = wilayah_objs[nama]
    cakupan = cakupan_objs.get((nama, wilayah.id))
    if not cakupan:
        # fallback kalau cakupan tidak ada (harusnya tidak terjadi)
        cakupan = db.query(glbm_wilayah_cakupan).filter_by(
            nama_wilayah=nama,
            wilayah_id=wilayah.id
        ).first()
    # Insert samsat
    existing_samsat = db.query(glbm_samsat).filter_by(kode_samsat=kode).first()
    if not existing_samsat:
        samsat = glbm_samsat(
            nama_samsat=nama,
            kode_samsat=kode,
            wilayah_id=wilayah.id,
            wilayah_cakupan_id=cakupan.id
        )
        db.add(samsat)
        print(f"✓ Tambah samsat: {kode} - {nama}")

db.commit()
db.close()
print("✅ Selesai menambahkan wilayah, cakupan, dan samsat.")