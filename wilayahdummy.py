from app.db.model import glbm_wilayah, glbm_wilayah_cakupan
from app.db.database import SessionLocal

# Inisialisasi session DB
db = SessionLocal()

# Buat data wilayah
wilayah1 = glbm_wilayah(
    nama_wilayah="Jakarta Selatan",
    kode_wilayah="JKT-SL"
)

wilayah2 = glbm_wilayah(
    nama_wilayah="Bandung",
    kode_wilayah="BDG"
)

# Commit wilayah terlebih dahulu untuk mendapatkan ID-nya
db.add_all([wilayah1, wilayah2])
db.commit()

# Refresh agar bisa ambil ID
db.refresh(wilayah1)
db.refresh(wilayah2)

# Buat cakupan wilayah (relasi dengan wilayah)
cakupan1 = glbm_wilayah_cakupan(
    nama_wilayah="Kebayoran Baru",
    wilayah_id=wilayah1.id
)

cakupan2 = glbm_wilayah_cakupan(
    nama_wilayah="Pasar Minggu",
    wilayah_id=wilayah1.id
)

cakupan3 = glbm_wilayah_cakupan(
    nama_wilayah="Cicendo",
    wilayah_id=wilayah2.id
)

cakupan4 = glbm_wilayah_cakupan(
    nama_wilayah="Antapani",
    wilayah_id=wilayah2.id
)

# Simpan ke database
db.add_all([cakupan1, cakupan2, cakupan3, cakupan4])
db.commit()

# Tutup session
db.close()
