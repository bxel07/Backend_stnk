import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from app.db.model import glbm_wilayah, glbm_wilayah_cakupan, glbm_samsat
from app.db.database import SessionLocal

db = SessionLocal()

# Step 1: Buat atau ambil wilayah "DKI & Serang"
wilayah_nama = "DKI & Serang"
cakupan_nama = "JABAR:B"

wilayah = db.query(glbm_wilayah).filter_by(nama_wilayah=wilayah_nama).first()
if not wilayah:
    wilayah = glbm_wilayah(nama_wilayah=wilayah_nama)
    db.add(wilayah)
    db.commit()
    db.refresh(wilayah)
    print(f"✓ Buat wilayah: {wilayah_nama}")
else:
    print(f"✓ Wilayah sudah ada: {wilayah_nama}")

# Step 2: Buat atau ambil cakupan "JABAR:B"
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
    print(f"✓ Buat cakupan: {cakupan_nama}")
else:
    print(f"✓ Cakupan sudah ada: {cakupan_nama}")

# Step 3: Daftar Samsat di JABAR:B (dari gambar yang kamu kasih)
samsat_jabar = [
    {"kode_samsat": "BKS", "nama_samsat": "Bekasi"},
    {"kode_samsat": "CKG", "nama_samsat": "Cikarang"},
    {"kode_samsat": "DPK", "nama_samsat": "Depok"},
    {"kode_samsat": "CNR", "nama_samsat": "Cinere"},
    # Tambahin sendiri sisanya dari daftar yang kamu punya
]

for data in samsat_jabar:
    samsat = db.query(glbm_samsat).filter_by(kode_samsat=data["kode_samsat"]).first()
    if not samsat:
        samsat = glbm_samsat(
            kode_samsat=data["kode_samsat"],
            nama_samsat=data["nama_samsat"],
            wilayah_id=wilayah.id,
            wilayah_cakupan_id=cakupan.id
        )
        db.add(samsat)
        print(f"✓ Tambah samsat: {data['kode_samsat']} - {data['nama_samsat']}")
    else:
        print(f"• Lewat (sudah ada): {data['kode_samsat']} - {data['nama_samsat']}")

db.commit()
db.close()
print("✅ SELESAI: Data samsat Jabar (cakupan JABAR:B) ditambahkan ke wilayah DKI & Serang.")
