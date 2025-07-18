'''
    Import Lib Untuk Utility
'''

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi.concurrency import run_in_threadpool
from openai import BaseModel
from requests import Session
import setuptools
import uuid
import shutil
import os
from functools import partial



'''
    Import Lib Untuk API
'''
from fastapi import FastAPI, Path, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException

'''
    Import Lib Untuk Utility
'''
from app.pipeline.extract_nomor_rangka import extract_nomor_rangka_fast
from paddlex import create_pipeline
# from app.pipeline.opt_extract_nomor_rangka import run_batch_processing
from app.pipeline.opt_ocr_extract_nomor_rangka import run_batch_processing



'''
    Import DB
'''
from app.db.database import Base, engine
from app.db.model import STNKData
from app.db.model import STNKFieldCorrection
from app.db.database import SessionLocal
from fastapi.staticfiles import StaticFiles
from paddleocr import PaddleOCR



'''
    Init Instance [app, middleware, pipeline ocr, DB]
'''

from contextlib import asynccontextmanager

# Dictionary untuk menyimpan model OCR yang sudah dimuat
# Ini akan diisi saat startup aplikasi.
ml_models: Dict[str, PaddleOCR] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Fungsi Lifespan untuk mengelola model PaddleOCR.
    Model dimuat saat startup dan dibersihkan saat shutdown.
    """
    # ====== STARTUP ======
    # Muat model PaddleOCR ke dalam memori.
    # Parameter bisa disesuaikan sesuai kebutuhan.
    # Contoh: use_gpu=True jika Anda memiliki GPU dan paddlepaddle-gpu terinstal.
    # lang='en' untuk bahasa Inggris, 'id' untuk Indonesia, atau 'ch' untuk Mandarin.
    print("Memuat model PaddleOCR...")
    # ml_models["ocr_model"] = create_pipeline('./my_path/OCR.yaml', device="cpu", use_hpip=False)
    ml_models["ocr_model"] = PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        use_doc_orientation_classify=True,
        use_textline_orientation=False,
        text_det_box_thresh=0.6,
        text_det_unclip_ratio=1.6,  
        lang='id'                               
    )
    print("Model PaddleOCR berhasil dimuat.")
    
    yield
    
    # ====== SHUTDOWN ======
    # Bersihkan sumber daya saat aplikasi berhenti.
    print("Membersihkan model OCR...")
    ml_models.clear()
    print("Sumber daya telah dibersihkan.")

app = FastAPI(root_path="/api", lifespan=lifespan)

app.mount("/storage", StaticFiles(directory="app/storage"), name="storage")

Base.metadata.create_all(bind=engine)

class CorrectionItem(BaseModel):
    field_name: str
    corrected_value: str

# Setup CORS

origins = [
    "*",
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://127.0.0.1:80",
    "http://127.0.0.1:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://8jnbbt04-5173.asse.devtunnels.ms/upload-stnk",
    "http://31.97.105.101",
    "https://31.97.105.101"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # Inisialisasi pipeline OCR sekali saat aplikasi dimulai
# pipeline = create_pipeline(pipeline="OCR")
'IMPORT TAMBAHAN'
from fastapi import FastAPI, HTTPException, Depends
from app.db.model import User, STNKData, STNKFieldCorrection, stpm_orlap, glbm_samsat, glbm_wilayah_cakupan , glbm_wilayah , Detail_otorisasi_samsat, otorisasi_samsat,RoleEnum,Role,glbm_brand,glbm_pt,master_excel
from app.db.database import engine
Base.metadata.create_all(bind=engine)  # Ganti path sesuai tempat kamu menyimpan enum-nya
from app.utils.auth import create_access_token
from datetime import datetime, timedelta
from app.middleware.login import LoginMiddleware
app.add_middleware(LoginMiddleware)
from app.utils.auth import require_role
from app.db.database import get_db
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session, joinedload
from app.utils.auth import get_current_user 
import pandas as pd
from pytz import timezone
from datetime import datetime

JAKARTA_TZ = timezone("Asia/Jakarta")







# Function untuk mengembalikan semua user
@app.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    users = db.query(User).all()
    result = []

    for user in users:
        all_detail = []
        for otorisasi in user.otorisasi_samsat:
            all_detail.extend(otorisasi.detail_otorisasi_samsat)

        # Hapus ini kalau tidak dibutuhkan di root:
        # brand_ids = list({d.glbm_brand_id for d in all_detail})
        # pt_ids = list({d.glbm_pt_id for d in all_detail})
        # samsat_ids = list({d.glbm_samsat_id for d in all_detail})

        # Filter otorisasi unik berdasarkan kombinasi pt_id & brand_id
        seen = set()
        otorisasi_clean = []
        for d in all_detail:
            key = (d.glbm_pt_id, d.glbm_brand_id)
            if key not in seen:
                seen.add(key)
                otorisasi_clean.append({
                    "pt_id": d.glbm_pt_id,
                    "brand_id": d.glbm_brand_id
                })

        result.append({
            "id": user.id,
            "username": user.username,
            "gmail": user.gmail,
            "role": user.role.role if user.role else None,
            # ⛔ HAPUS pt_id, brand_ids, samsat_id dari sini
            "otorisasi": otorisasi_clean
        })

    return {"data": result}


@app.get("/roles")
def get_roles(db: Session = Depends(get_db)):
    roles = db.query(Role).all()
    return [{"id": role.id, "name": role.role.value} for role in roles]


class LoginData(BaseModel):
    username: str
    password: str




@app.post("/login")
def login(data: LoginData):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == data.username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        token = create_access_token({"sub" : str(user.id), "role": user.role.role})

        if user and user.hashed_password == data.password:
            return {
                "access_token": token,
                "token_type": "bearer",
                "message": "Login berhasil",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.role.value
                }
            }

        raise HTTPException(status_code=401, detail="Username atau password salah")

    finally:
        db.close()
        
    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegisterData(BaseModel):
    username: str
    gmail: EmailStr
    password: str
    role_id: int
    nama_lengkap: str
    nomor_telepon: str
    glbm_brand_ids: Optional[List[int]] = []
    glbm_pt_id: Optional[List[int]] = []
    glbm_samsat_id: int

@app.post("/register")
def register(data: RegisterData, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")
    if db.query(User).filter(User.gmail == data.gmail).first():
        raise HTTPException(status_code=400, detail="Gmail sudah terdaftar")

    try:
        biodata = stpm_orlap(
            nama_lengkap=data.nama_lengkap,
            nomor_telepon=data.nomor_telepon
        )
        db.add(biodata)
        db.flush()

        user = User(
            username=data.username,
            hashed_password=data.password,
            gmail=data.gmail,
            role_id=data.role_id,
            stpm_orlap_id=biodata.id
        )
        db.add(user)
        db.flush()

        otorisasi = otorisasi_samsat(
            user_id=user.id,
            created_at=datetime.now(JAKARTA_TZ),
            updated_at=datetime.now(JAKARTA_TZ)
        )
        db.add(otorisasi)
        db.flush()

        samsat = db.query(glbm_samsat).filter(glbm_samsat.id == data.glbm_samsat_id).first()
        if not samsat:
            raise HTTPException(status_code=400, detail="Samsat tidak ditemukan")

        wilayah_id = samsat.wilayah_id
        wilayah_cakupan_id = samsat.wilayah_cakupan_id

        # Kombinasi semua PT dan Brand
        pt_ids = data.glbm_pt_id if data.glbm_pt_id else [None]
        brand_ids = data.glbm_brand_ids if data.glbm_brand_ids else [None]

        for pt_id in pt_ids:
            for brand_id in brand_ids:
                detail = Detail_otorisasi_samsat(
                    glbm_samsat_id=data.glbm_samsat_id,
                    wilayah_id=wilayah_id,
                    wilayah_cakupan_id=wilayah_cakupan_id,
                    glbm_brand_id=brand_id,
                    glbm_pt_id=pt_id,
                    otorisasi_samsat_id=otorisasi.id
                )
                db.add(detail)

        db.commit()
        return {"message": "Registrasi berhasil"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Registrasi gagal: {e}")



class otorisasiUpdate(BaseModel):
    brand_id: Optional[int] = None
    pt_id: Optional[int] = None

class UpdateUserData(BaseModel):
    username: Optional[str]
    gmail: Optional[str]
    role_id: Optional[int]
    otorisasi: Optional[List[otorisasiUpdate]]

@app.put("/update-user/{user_id}")
def update_user(
    user_id: int,
    data: UpdateUserData,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        # Cari user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")

        # === Update data user umum ===
        if data.username:
            user.username = data.username
        if data.gmail:
            user.gmail = data.gmail
        if data.role_id:
            role = db.query(Role).filter(Role.id == data.role_id).first()
            if not role:
                raise HTTPException(status_code=404, detail="Role tidak ditemukan")
            user.role_id = role.id

        # === Update otorisasi: brand & pt ===
        if data.otorisasi:
            # Ambil semua otorisasi milik user
            otorisasi_list = db.query(otorisasi_samsat).filter(
                otorisasi_samsat.user_id == user.id
            ).all()

            detail_index = 0

            for otor in otorisasi_list:
                detail_list = db.query(Detail_otorisasi_samsat).filter(
                    Detail_otorisasi_samsat.otorisasi_samsat_id == otor.id
                ).all()

                for detail in detail_list:
                    if detail_index >= len(data.otorisasi):
                        break  # kalau input lebih sedikit dari jumlah detail
                    otor_data = data.otorisasi[detail_index]

                    # Update brand & pt
                    detail.glbm_brand_id = otor_data.brand_id
                    detail.glbm_pt_id = otor_data.pt_id

                    db.add(detail)
                    detail_index += 1

        db.commit()
        db.refresh(user)

        return {
            "message": "User dan detail otorisasi berhasil diperbarui",
            "user": {
                "id": user.id,
                "username": user.username,
                "gmail": user.gmail,
                "role": user.role.role.value
            }
        }

    except Exception as e:
        db.rollback()
        print("ERROR UPDATE USER:", str(e))
        raise HTTPException(status_code=500, detail="Terjadi kesalahan saat memperbarui user")

@app.get("/user-profile")
def get_user_profile(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = int(current_user["sub"])

    # Ambil user dan relasinya
    user = db.query(User).options(
        joinedload(User.role),
        joinedload(User.stpm_orlap)
    ).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    profile = {
        "id": user.id,
        "username": user.username,
        "gmail": user.gmail,
        "role": user.role.role if user.role else None,
        "nama_lengkap": user.stpm_orlap.nama_lengkap if user.stpm_orlap else None,
        "nomor_telepon": user.stpm_orlap.nomor_telepon if user.stpm_orlap else None,
        "otorisasi": []
    }

    # Ambil otorisasi
    otorisasi_list = db.query(Detail_otorisasi_samsat).join(otorisasi_samsat).filter(
        otorisasi_samsat.user_id == user.id
    ).all()

    for detail in otorisasi_list:
        samsat = db.query(glbm_samsat).filter(glbm_samsat.id == detail.glbm_samsat_id).first()
        brand = db.query(glbm_brand).filter(glbm_brand.id == detail.glbm_brand_id).first()
        pt = db.query(glbm_pt).filter(glbm_pt.id == detail.glbm_pt_id).first()

        profile["otorisasi"].append({
            "samsat_id": samsat.id if samsat else None,
            "samsat_nama": samsat.nama_samsat if samsat else None,
            "pt_id": pt.id if pt else None,
            "pt_nama": pt.nama_pt if pt else None,
            "brand_id": brand.id if brand else None,
            "brand_nama": brand.nama_brand if brand else None
        })

    return profile
class UpdateUserProfile(BaseModel):
    password: Optional[str] = None

@app.put("/user-profile/update")
def update_user_profile(
     request: UpdateUserProfile,
     current_user : dict = Depends(get_current_user),
     db: Session = Depends(get_db)
):
    try:
        user_id = int(current_user.get("sub"))  # Ambil user_id dari token
        user = db.query(User).options(joinedload(User.stpm_orlap)).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")

        if request.password:
            user.hashed_password = request.password  # ⚠️ hash sebaiknya digunakan di real app

        db.commit()
        db.refresh(user)

        return {
            "message": "Password berhasil diperbarui",
        }
    except Exception as e:
        print("ERROR UPDATE USER:", str(e))



@app.delete("/delete-user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(require_role(RoleEnum.ADMIN, RoleEnum.SUPERADMIN))):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")

        db.delete(user)
        db.commit()

        return {"message": "User berhasil dihapus"}
    except Exception as e:
        print("ERROR DELETE USER:", str(e))



@app.get("/glbm-samsat/")
def get_glbm_samsat(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:    
        samsats = db.query(glbm_samsat).options(
            joinedload(glbm_samsat.wilayah_cakupan),
            joinedload(glbm_samsat.wilayah)
        ).all()

        data = []
        for samsat in samsats:
            wilayah_cakupan = samsat.wilayah_cakupan
            wilayah = samsat.wilayah

            data.append({
                "id": samsat.id,
                "nama_samsat": samsat.nama_samsat,
                "kode_samsat": samsat.kode_samsat,
                "wilayah_cakupan": wilayah_cakupan.nama_wilayah if wilayah_cakupan else None,
                "wilayah": wilayah.nama_wilayah if wilayah else None,
            })

        return {"status": "success", "data": data}

    except Exception as e:
        return {"status": "error", "message": str(e)}

class AddSamsatRequest(BaseModel):
    nama_samsat: str
    kode_samsat: str
    wilayah_cakupan_id: int  # ID dari glbm_wilayah_cakupan

    class Config:
        orm_mode = True


@app.post("/glbm-samsat/")
def add_glbm_samsat(
    request: AddSamsatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        # Cari wilayah_id dari tabel glbm_wilayah_cakupan
        cakupan = db.query(glbm_wilayah_cakupan).filter(
            glbm_wilayah_cakupan.id == request.wilayah_cakupan_id
        ).first()

        if not cakupan:
            return {"status": "error", "message": "Wilayah cakupan tidak ditemukan"}

        # Ambil wilayah_id dari cakupan yang ditemukan
        wilayah_id = cakupan.wilayah_id

        # Simpan data samsat
        new_glbm_samsat = glbm_samsat(
            nama_samsat=request.nama_samsat,
            kode_samsat=request.kode_samsat,
            wilayah_cakupan_id=request.wilayah_cakupan_id,
            wilayah_id=wilayah_id  # ← otomatis
        )
        db.add(new_glbm_samsat)
        db.commit()
        db.refresh(new_glbm_samsat)

        return {
            "status": "success",
            "data": {
                "id": new_glbm_samsat.id,
                "nama_samsat": new_glbm_samsat.nama_samsat,
                "kode_samsat": new_glbm_samsat.kode_samsat,
                "wilayah_id": wilayah_id,
                "wilayah_cakupan_id": request.wilayah_cakupan_id
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/detail-otorisasi-samsat")
def get_detail_otorisasi_samsat(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        # Ambil seluruh data cakupan wilayah beserta relasinya
        cakupan_list = db.query(glbm_wilayah_cakupan).options(
            joinedload(glbm_wilayah_cakupan.wilayah),
            joinedload(glbm_wilayah_cakupan.detail_otorisasi_samsat).joinedload(Detail_otorisasi_samsat.glbm_samsat)
        ).all()

        data = []
        for cakupan in cakupan_list:
            wilayah = cakupan.wilayah
            data.append({
                "id_wilayah_cakupan": cakupan.id,
                "nama_wilayah_cakupan": cakupan.nama_wilayah,
                "wilayah_induk": wilayah.nama_wilayah if wilayah else None,
                "detail_otorisasi_samsat": [
                    {
                        "id": d.id,
                        "glbm_samsat_id": d.glbm_samsat_id,
                        "glbm_samsat_nama": d.glbm_samsat.nama_samsat if d.glbm_samsat else None,
                    }
                    for d in cakupan.detail_otorisasi_samsat
                ]
            })

        return {"status": "success", "data": data}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/otorisasi-samsat")
def get_otorisasi_samsat(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        otorisasi_list = db.query(otorisasi_samsat).options(
            joinedload(otorisasi_samsat.user),
            joinedload(otorisasi_samsat.detail_otorisasi_samsat)
                .joinedload(Detail_otorisasi_samsat.glbm_samsat),
            joinedload(otorisasi_samsat.detail_otorisasi_samsat)
                .joinedload(Detail_otorisasi_samsat.detail_wilayah_cakupan)
                .joinedload(glbm_wilayah_cakupan.wilayah)
        ).all()

        data = []
        for item in otorisasi_list:
            detail = item.detail_otorisasi_samsat
            samsat = detail.glbm_samsat if detail else None
            wilayah = detail.detail_wilayah_cakupan if detail else None
            user = item.user
            wilayah_induk = wilayah.wilayah if wilayah else None

            data.append({
                "id": item.id,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "user_id": user.id if user else None,
                "username": user.username if user else None,
                "glbm_samsat_id": samsat.id if samsat else None,
                "glbm_samsat_nama": samsat.nama_samsat if samsat else None,
                "wilayah_cakupan_id": wilayah.id if wilayah else None,
                "wilayah_cakupan_nama": wilayah.nama_wilayah if wilayah else None,
                "wilayah_induk_nama": wilayah_induk.nama_wilayah if wilayah_induk else None,

            })

        return {"status": "success", "data": data}

    except Exception as e:
        return {"status": "error", "message": str(e)}


class otorisasiRequest(BaseModel):
    user_id: int
    detail_otorisasi_samsat_id: Optional[int] = None
    detail_otorisasi_samsat_ids: Optional[List[int]] = None

@app.post("/add-otorisasi-samsat")
def add_otorisasi_samsat(
    request: otorisasiRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.ADMIN, RoleEnum.CAO, RoleEnum.SUPERADMIN))
):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # Mode Multiple
    if request.detail_otorisasi_samsat_ids:
        results = []
        for detail_id in request.detail_otorisasi_samsat_ids:
            detail = db.query(Detail_otorisasi_samsat).filter_by(id=detail_id).first()
            if not detail:
                continue  # Lewatkan kalau tidak ditemukan

            existing = db.query(otorisasi_samsat).filter_by(
                user_id=request.user_id,
                detail_otorisasi_samsat_id=detail_id
            ).first()
            if existing:
                continue

            new_otorisasi = otorisasi_samsat(
                user_id=request.user_id,
                detail_otorisasi_samsat_id=detail_id
            )
            db.add(new_otorisasi)
            db.commit()
            db.refresh(new_otorisasi)

            results.append({
                "user_id": new_otorisasi.user_id,
                "detail_otorisasi_samsat_id": new_otorisasi.detail_otorisasi_samsat_id
            })

        return {
            "status": "success",
            "message": f"{len(results)} otorisasi berhasil ditambahkan",
            "data": results
        }

    # Mode Single
    elif request.detail_otorisasi_samsat_id:
        detail = db.query(Detail_otorisasi_samsat).filter_by(id=request.detail_otorisasi_samsat_id).first()
        if not detail:
            raise HTTPException(status_code=404, detail="Detail otorisasi tidak ditemukan")

        existing = db.query(otorisasi_samsat).filter_by(
            user_id=request.user_id,
            detail_otorisasi_samsat_id=request.detail_otorisasi_samsat_id
        ).first()
        if existing:
            return {
                "status": "error",
                "message": "User sudah memiliki otorisasi ini"
            }

        new_otorisasi = otorisasi_samsat(
            user_id=request.user_id,
            detail_otorisasi_samsat_id=request.detail_otorisasi_samsat_id
        )
        db.add(new_otorisasi)
        db.commit()
        db.refresh(new_otorisasi)

        return {
            "status": "success",
            "message": "otorisasi berhasil ditambahkan",
            "data": {
                "user_id": new_otorisasi.user_id,
                "detail_otorisasi_samsat_id": new_otorisasi.detail_otorisasi_samsat_id
            }
        }

    # Tidak ada field yang dikirim
    else:
        raise HTTPException(
            status_code=400,
            detail="Harus menyertakan salah satu dari 'detail_otorisasi_samsat_id' atau 'detail_otorisasi_samsat_ids'"
        )

@app.get("/wilayah")
def get_wilayah(db: Session = Depends(get_db)):
    try:
        wilayah_list = db.query(glbm_wilayah).all()
        data = []
        for wilayah in wilayah_list:
            data.append({
                "id": wilayah.id,
                "nama_wilayah": wilayah.nama_wilayah,
                "cakupan": [
                    {
                        "id": cakupan.id,
                        "nama_wilayah": cakupan.nama_wilayah
                    } for cakupan in wilayah.wilayah_cakupan
                ]
            })
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AddWilayahRequest(BaseModel):
    nama_wilayah: str

    class Config:
        orm_mode = True

@app.post("/wilayah")
def add_wilayah(
    request: AddWilayahRequest,
    db: Session = Depends(get_db)
):
    try:
        new_wilayah = glbm_wilayah(nama_wilayah=request.nama_wilayah)
        db.add(new_wilayah)
        db.commit()
        db.refresh(new_wilayah)
        return {"status": "success", "data": new_wilayah}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AddWilayahCakupanRequest(BaseModel):
    nama_wilayah: str
    wilayah_id: int  # ID dari glbm_wilayah

    class Config:
        orm_mode = True

@app.post("/wilayah-cakupan")
def add_wilayah_cakupan(
    request: AddWilayahCakupanRequest,
    db: Session = Depends(get_db)
):
    try:
        # Cek apakah wilayah dengan ID tersebut ada
        wilayah = db.query(glbm_wilayah).filter(glbm_wilayah.id == request.wilayah_id).first()
        if not wilayah:
            return {"status": "error", "message": "Wilayah tidak ditemukan"}

        # Buat cakupan wilayah baru
        new_cakupan = glbm_wilayah_cakupan(
            nama_wilayah=request.nama_wilayah,
            wilayah_id=request.wilayah_id
        )

        db.add(new_cakupan)
        db.commit()
        db.refresh(new_cakupan)

        return {"status": "success", "data": new_cakupan}
    except Exception as e:
        return {"status": "error", "message": str(e)}


import pandas as pd
import io
from fastapi import UploadFile, File, HTTPException


@app.get("/glbm-pt")
def get_glbm_pt(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        pt_list = db.query(glbm_pt).all()
        data = []
        for pt in pt_list:
            data.append({
                "id": pt.id,
                "nama_pt": pt.nama_pt,
                "kode_pt": pt.kode_pt
            })
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AddPtRequest(BaseModel):
    nama_pt: str
    kode_pt: str

    class Config:
        orm_mode = True

@app.post("/add-pt")
def add_pt(
    request: AddPtRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        # Cek apakah PT dengan nama yang sama sudah ada
        existing_pt = db.query(glbm_pt).filter(glbm_pt.nama_pt == request.nama_pt).first()
        if existing_pt:
            return {"status": "error", "message": "PT dengan nama ini sudah ada"}

        # Buat data PT baru
        new_pt = glbm_pt(
            nama_pt=request.nama_pt,
            kode_pt=request.kode_pt
        )

        db.add(new_pt)
        db.commit()
        db.refresh(new_pt)

        return {
            "status": "success",
            "data": {
                "id": new_pt.id,
                "nama_pt": new_pt.nama_pt,
                "kode_pt": new_pt.kode_pt
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/glbm-brand")
def get_glbm_brand(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        brand_list = db.query(glbm_brand).all()
        data = []
        for brand in brand_list:
            data.append({
                "id": brand.id,
                "nama_brand": brand.nama_brand,
                "kode_brand": brand.kode_brand
            })
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AddBrandRequest(BaseModel):
    nama_brand: str
    kode_brand: str

    class Config:
        orm_mode = True

@app.post("/add-brand")
def add_brand(
    request: AddBrandRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        # Cek apakah brand dengan nama yang sama sudah ada
        existing_brand = db.query(glbm_brand).filter(glbm_brand.nama_brand == request.nama_brand).first()
        if existing_brand:
            return {"status": "error", "message": "Brand dengan nama ini sudah ada"}

        # Buat data brand baru
        new_brand = glbm_brand(
            nama_brand=request.nama_brand,
            kode_brand=request.kode_brand
        )

        db.add(new_brand)
        db.commit()
        db.refresh(new_brand)

        return {
            "status": "success",
            "data": {
                "id": new_brand.id,
                "nama_brand": new_brand.nama_brand,
                "kode_brand": new_brand.kode_brand
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}



@app.get("/")
def read_root():
    return {"Hello": "World"}


    db.close()

from sqlalchemy.orm import joinedload


from sqlalchemy.orm import joinedload
from sqlalchemy import or_


@app.get("/stnk-data/")
def get_all_stnk_data(current_user: dict = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        role = current_user.get("role")
        user_id = int(current_user.get("sub"))
        query = db.query(STNKData)

        if role == "superadmin":
            stnk_entries = db.query(STNKData).join(
                master_excel,
                STNKData.nomor_rangka == master_excel.norangka
            ).all()

        elif role == "cao":
            otorisasi_rows = db.query(Detail_otorisasi_samsat).join(
                otorisasi_samsat,
                otorisasi_samsat.id == Detail_otorisasi_samsat.otorisasi_samsat_id
            ).filter(
                otorisasi_samsat.user_id == user_id
            ).all()

            wilayah_cakupan_ids = set(row.wilayah_cakupan_id for row in otorisasi_rows)
            brand_ids = set(row.glbm_brand_id for row in otorisasi_rows if row.glbm_brand_id is not None)

            brand_names = []
            if brand_ids:
                brand_names = [b.nama_brand for b in db.query(glbm_brand).filter(glbm_brand.id.in_(brand_ids)).all()]

            uploaded_user_ids = [u[0] for u in db.query(STNKData.user_id).distinct().all()]

            user_ids_eligible = set()
            for uid in uploaded_user_ids:
                user_otorisasi_rows = db.query(Detail_otorisasi_samsat).join(
                    otorisasi_samsat,
                    otorisasi_samsat.id == Detail_otorisasi_samsat.otorisasi_samsat_id
                ).filter(
                    otorisasi_samsat.user_id == uid
                ).all()

                for row in user_otorisasi_rows:
                    if row.wilayah_cakupan_id in wilayah_cakupan_ids:
                        user_ids_eligible.add(uid)
                        break

            query = db.query(STNKData).join(
                master_excel,
                STNKData.nomor_rangka == master_excel.norangka
            ).filter(STNKData.user_id.in_(user_ids_eligible))

            if brand_names:
                query = query.filter(STNKData.nama_brand.in_(brand_names))

            stnk_entries = query.all()

        elif role == "admin":
            otorisasi_rows = db.query(Detail_otorisasi_samsat).join(
                otorisasi_samsat,
                otorisasi_samsat.id == Detail_otorisasi_samsat.otorisasi_samsat_id
            ).filter(
                otorisasi_samsat.user_id == user_id
            ).all()

            wilayah_ids = set(row.wilayah_id for row in otorisasi_rows)
            pt_ids = set(row.glbm_pt_id for row in otorisasi_rows if row.glbm_pt_id is not None)

            pt_names = []
            if pt_ids:
                pt_names = [b.nama_pt for b in db.query(glbm_pt).filter(glbm_pt.id.in_(pt_ids)).all()]

            uploaded_user_ids = [u[0] for u in db.query(STNKData.user_id).distinct().all()]

            user_ids_eligible = set()
            for uid in uploaded_user_ids:
                user_otorisasi_rows = db.query(Detail_otorisasi_samsat).join(
                    otorisasi_samsat,
                    otorisasi_samsat.id == Detail_otorisasi_samsat.otorisasi_samsat_id
                ).filter(
                    otorisasi_samsat.user_id == uid
                ).all()

                for row in user_otorisasi_rows:
                    if row.wilayah_id in wilayah_ids:
                        user_ids_eligible.add(uid)
                        break

            query = db.query(STNKData).join(
                master_excel,
                STNKData.nomor_rangka == master_excel.norangka
            ).filter(STNKData.user_id.in_(user_ids_eligible))

            if pt_names:
                query = query.filter(STNKData.nama_pt.in_(pt_names))

            stnk_entries = query.all()

        elif role == "user":
            stnk_entries = query.filter(STNKData.user_id == user_id).all()

        else:
            return {"status": "forbidden", "message": "Anda tidak memiliki akses"}

        # Format hasil
        data = []
        for entry in stnk_entries:
            entry_dict = entry.__dict__.copy()
            entry_dict.pop("_sa_instance_state", None)

            if entry.path:
                relative_path = os.path.relpath(entry.path, start="app")
                image_url = f"/{relative_path.replace(os.sep, '/')}"
            else:
                image_url = None

            entry_dict["image_url"] = image_url
            data.append(entry_dict)

        print(data)
        return {"status": "success", "data": data}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        db.close()


@app.get("/stnk-data/with-correction/")
def get_ktp_data_with_corrections(current_user=Depends(require_role(RoleEnum.ADMIN, RoleEnum.SUPERADMIN))):
    db = SessionLocal()
    stnk_entries = db.query(STNKData).all()
    corrected_entries = []

    for entry in stnk_entries:
        corrected_data = entry.__dict__.copy()
        corrections = db.query(STNKFieldCorrection).filter(STNKFieldCorrection.stnk_data_id == entry.id).all()

        for corr in corrections:
            # Jika corrected_value TIDAK kosong/null, baru timpa data asli
            if corr.corrected_value not in [None, ""] and corr.field_name in corrected_data:
                corrected_data[corr.field_name] = corr.corrected_value

        # Hapus field SQLAlchemy internal state
        corrected_data.pop("_sa_instance_state", None)
        corrected_entries.append(corrected_data)

    db.close()
    return {"data": corrected_entries}

# Pydantic model for save request
class STNKSaveRequest(BaseModel):
    filename: str
    nomor_rangka: str
    corrected: Optional[bool] = False
    original_nomor_rangka: Optional[str] = None

# Endpoint 1: Extract data only (no database save)
# @app.post("/upload-stnk/")
# async def upload_stnk(file: UploadFile = File(...)):
#     """
#     Extract data from STNK image without saving to database
#     Returns the extracted information for user review
#     """
#     temp_path = f"temp_{file.filename}"
    
#     try:
#         # Save uploaded file temporarily
#         with open(temp_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
        
#         # Process the image using your pipeline
#         output = pipeline.predict(
#             input=temp_path,
#             use_doc_orientation_classify=True,
#             use_doc_unwarping=True,
#             use_textline_orientation=True,
#         )
        
#         # Extract nomor rangka and other information
#         nomor_rangka, info, texts = extract_nomor_rangka_fast(output)
        
#         # Return extracted data without saving
#         return {
#             "status": "success",
#             "filename": file.filename,
#             "nomor_rangka": nomor_rangka,
#             "full_text": texts,
#             "info": info,
#             "message": "Data extracted successfully. Please review and confirm."
#         }
        
#     except Exception as e:
#         return {
#             "status": "error", 
#             "message": f"Error extracting data: {str(e)}"
#         }
    
#     finally:
#         # Clean up temporary file
#         if os.path.exists(temp_path):
#             os.remove(temp_path)

# =============================================================================
# ENDPOINT API TERINTEGRASI
# =============================================================================

@app.post("/upload-stnk-batch/")
async def upload_stnk_batch(
    files: List[UploadFile] = File(..., description="Unggah hingga 10 gambar STNK untuk diproses."),
    db: Session = Depends(get_db)  # ✅ Inject DB session di sini
):
    """
    Endpoint terintegrasi yang melakukan:
    1. Menerima unggahan batch gambar (maksimal 10 file).
    2. Menyimpan file-file tersebut ke direktori sementara yang unik.
    3. **Memanggil fungsi pemrosesan OCR untuk direktori tersebut secara non-blocking.**
    4. Mengembalikan hasil lengkap dari pemrosesan OCR.
    5. **Membersihkan direktori sementara secara otomatis setelah selesai.**
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=400, 
            detail="Error: Maksimal 10 file yang dapat diunggah sekaligus."
        )

    batch_id = str(uuid.uuid4())
    # Pastikan direktori 'app/storage' ada atau dapat dibuat
    storage_path = os.path.join("app", "storage")
    batch_dir = os.path.join(storage_path, f"batch_{batch_id}")
    os.makedirs(batch_dir, exist_ok=True)

    try:
        # 3. Simpan semua file yang diunggah ke direktori sementara
        for file in files:
            try:
                file_path = os.path.join(batch_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            finally:
                await file.close()

        # 4. JALANKAN PROSES OCR YANG BERAT DI THREAD TERPISAH
        # Ini adalah langkah kuncinya. Kita memberitahu FastAPI untuk menjalankan
        # fungsi 'process_batch_images' yang blocking di thread pool.
        # 'await' menunggu hasilnya tanpa memblokir event-loop utama.
        processing_results = await run_in_threadpool(
            partial(run_batch_processing, batch_directory=batch_dir, pipeline_path=ml_models["ocr_model"], candidate_count=10, db=db)
        )

        # all_norangka= {row.norangka for row in db.query(master_excel.norangka).all()}
        
        # for result in processing_results:
        #     norangka = result.get("nomor_rangka")
        #     if norangka not in all_norangka:
        #         result["nomor_rangka"] = "-"
        print(processing_results)
        return processing_results

        # # 5. Kembalikan hasil dari fungsi pemrosesan
        # return {
        #     "user_id": current_user.id,
        #     "results": processing_results
        # }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Terjadi error yang tidak terduga pada level server: {str(e)}"
        )
    finally:
        # 6. PEMBERSIHAN
        # Blok 'finally' akan selalu dieksekusi, baik proses berhasil atau gagal.
        # Ini memastikan tidak ada file sampah yang tertinggal di server.
        if os.path.exists(batch_dir):
            # shutil.rmtree(batch_dir)
            print(f"INFO: Direktori sementara '{batch_dir}' telah berhasil dihapus.")
class STNKDetail(BaseModel):
    jumlah: Optional[int] = None

class STNKSaveRequest(BaseModel):
    nomor_rangka: str
    filename: str
    path: str
    kode_samsat: Optional[str] = None
    details: Optional[STNKDetail] = None

from sqlalchemy import text


@app.post("/save-stnk-data/")
async def save_data_stnk(request: STNKSaveRequest, current_user: dict = Depends(get_current_user)):
    db: Session = SessionLocal()

    try:
        print(f"Received request: {request}")

        if not request.nomor_rangka or request.nomor_rangka.strip() in ["", "-"]:
            raise HTTPException(status_code=400, detail="Nomor rangka tidak boleh kosong")

        nomor_rangka_clean = request.nomor_rangka.strip()

        # Cek apakah nomor rangka sudah ada
        existing = db.query(STNKData).filter(
            STNKData.nomor_rangka == nomor_rangka_clean
        ).first()
        if existing:
            return {
                "status": "error",
                "message": "Nomor rangka sudah ada di database"
            }

        # PRIORITAS 1: Cari dari master_excel berdasarkan nomor rangka
        nama_brand = None
        nama_pt = None
        final_kode_samsat = None


        print(f"Mencari data untuk nomor rangka: {nomor_rangka_clean}")
        
        try:
            master_excel_query = text("""
                SELECT merk, nama_pt, kode_samsat
                FROM master_excel 
                WHERE norangka = :nomor_rangka
                LIMIT 1
            """)
            master_result = db.execute(master_excel_query, {"nomor_rangka": nomor_rangka_clean}).fetchone()

            if master_result:
                nama_brand = master_result[0] or None
                nama_pt = master_result[1] or None
                final_kode_samsat = master_result[2] or None
                print(f"✅ Data ditemukan di master_excel: brand={nama_brand}, pt={nama_pt}, samsat={final_kode_samsat}")
            else:
                print("❌ Data tidak ditemukan di master_excel")
        except Exception as e:
            print(f"❌ Error query master_excel: {str(e)}")

        # Rename file
        old_path = request.path
        old_dir = os.path.dirname(old_path)
        ext = os.path.splitext(request.filename)[1]
        new_filename = f"{nomor_rangka_clean}{ext}"
        new_path = os.path.join(old_dir, new_filename)

        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                print(f"File renamed from {old_path} to {new_path}")
            else:
                print(f"[WARNING] File tidak ditemukan: {old_path}")
        except Exception as e:
            print(f"[ERROR] Gagal mengganti nama file: {e}")
            new_path = old_path
            new_filename = request.filename

        jumlah_value = request.details.jumlah if request.details else None
        user_id = int(current_user.get("sub"))

        stnk_entry = STNKData(
            file=new_filename,
            path=new_path,
            user_id=user_id,
            kode_samsat=final_kode_samsat,
            nomor_rangka=nomor_rangka_clean,
            jumlah=jumlah_value,
            nama_pt=nama_pt,
            nama_brand=nama_brand
        )

        db.add(stnk_entry)
        db.commit()
        db.refresh(stnk_entry)

        return {
            "status": "success",
            "message": "STNK data berhasil disimpan",
            "data": {
                "id": stnk_entry.id,
                "filename": stnk_entry.file,
                "nomor_rangka": stnk_entry.nomor_rangka,
                "jumlah": stnk_entry.jumlah,
                "kode_samsat": stnk_entry.kode_samsat,
                "user_id": stnk_entry.user_id,
                "nama_pt": stnk_entry.nama_pt,
                "nama_brand": stnk_entry.nama_brand,
                "created_at": stnk_entry.created_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error saving data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving data: {str(e)}")
    finally:
        db.close()

        


class UpdateSTNKRequest(BaseModel):
    nomor_rangka: str
    jumlah: int

@app.put("/stnk-data/{stnk_id}/update-info/")
def update_stnk_data_info(
    stnk_id: int = Path(..., description="ID data STNK yang ingin diperbarui"),current_user=Depends(require_role(RoleEnum.ADMIN, RoleEnum.SUPERADMIN)),
    payload: UpdateSTNKRequest = ... 
):
    db: Session = SessionLocal()
    try:
        stnk_entry = db.query(STNKData).filter(STNKData.id == stnk_id).first()
        if not stnk_entry:
            raise HTTPException(status_code=404, detail="Data STNK tidak ditemukan")

        stnk_entry.nomor_rangka = payload.nomor_rangka
        stnk_entry.jumlah = payload.jumlah

        db.commit()
        return {"status": "success", "message": "Data STNK berhasil diperbarui"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal memperbarui data: {str(e)}")

    finally:
        db.close()

@app.put("/stnk-data/{stnk_id}/correction/")
def update_corrections(stnk_id: int, corrections: List[CorrectionItem]):
    db = SessionLocal()
    try:
        # Periksa apakah data STNK ada
        stnk_entry = db.query(STNKData).filter(STNKData.id == stnk_id).first()
        if not stnk_entry:
            raise HTTPException(status_code=404, detail="STNK data not found")

        for item in corrections:
            # Skip jika field_name atau corrected_value kosong/null
            if not item.field_name or not item.corrected_value:
                continue

            correction_entry = db.query(STNKFieldCorrection).filter(
                STNKFieldCorrection.stnk_data_id == stnk_id,
                STNKFieldCorrection.field_name == item.field_name
            ).first()

            if correction_entry:
                correction_entry.corrected_value = item.corrected_value
            else:
                new_entry = STNKFieldCorrection(
                    stnk_data_id=stnk_id,  # ✅ Sesuai nama kolom foreign key
                    field_name=item.field_name,
                    corrected_value=item.corrected_value
                )
                db.add(new_entry)

        db.commit()
        return {"status": "success", "message": "Corrections updated successfully"}

    except Exception as e:
        db.rollback()  # Pastikan rollback jika error
        return {"status": "error", "message": str(e)}

    finally:
        db.close()

@app.get("/stnk-data/by-created-date/")
def get_stnk_data_by_created_date(date: str = Query(..., description="Tanggal dalam format YYYY-MM-DD")):
    db = SessionLocal()
    try:
        # Konversi string ke datetime
        target_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Tentukan rentang dari awal sampai akhir hari tersebut
        start_datetime = target_date
        end_datetime = target_date + timedelta(days=1)

        # Query entri yang created_at-nya di tanggal tersebut
        entries = db.query(STNKData).filter(
            STNKData.created_at >= start_datetime,
            STNKData.created_at < end_datetime
        ).order_by(STNKData.created_at.desc()).all()

        results = []
        for entry in entries:
            data = entry.__dict__.copy()
            data.pop("_sa_instance_state", None)
            results.append(data)

        return {
            "status": "success",
            "date": date,
            "count": len(results),
            "data": results
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal salah. Gunakan format YYYY-MM-DD.")
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

from io import BytesIO

# @app.post("/import-excel")
# async def import_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     try:
#         contents = await file.read()
#         df = pd.read_excel(io.BytesIO(contents))

#         records = []
#         for _, row in df.iterrows():
#             record = master_excel(
#                 norangka=row["norangka"],
#                 nama_stnk=row["nama_stnk"],
#                 kode_tipe=row["KodeTipe"],
#                 tipe=row["tipe"],
#                 kode_model=row["KodeModel"],
#                 model=row["model"],
#                 merk=row["merk"],
#                 kode_samsat=row["kodesamsat"],
#                 samsat=row["samsat"],
#                 kode_dealer=str(row["kodedealer"]),  # Pastikan dikonversi ke string
#                 nama_dealer=row["NamaDealer"],
#                 kode_group=row["KodeGroup"],
#                 group_perusahaan=row["groupperusahaan"],
#                 tgl_mohon_stnk=row["tglmohonstnk"].date() if pd.notna(row["tglmohonstnk"]) else None,
#                 tgl_simpan=row["TglSimpan"].date() if pd.notna(row["TglSimpan"]) else None,
#                 nama_pt=row["namaPT"],
#                 kode_cabang=row["kode_cabang"]
#             )
#             records.append(record)

#         db.bulk_save_objects(records)
#         db.commit()

#         return {"message": f"{len(records)} data berhasil diimpor"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Gagal mengimpor data: {e}")

from datetime import date 
class MasterExcelSchema(BaseModel):
    norangka: str
    nama_stnk: str
    kode_tipe: str
    tipe: str
    kode_model: str
    model: str
    merk: str
    kode_samsat: str
    samsat: str
    kode_dealer: str
    nama_dealer: str
    kode_group: str
    group_perusahaan: str
    tgl_mohon_stnk: date
    tgl_simpan: date
    nama_pt: str
    kode_cabang: str



@app.post("/import-excel")
async def import_from_json(
    data: List[MasterExcelSchema],
    db: Session = Depends(get_db)
):
    try:
        if not data:
            return JSONResponse(status_code=422, content={
                "status": "error",
                "status_code": 422,
                "message": "Data tidak boleh kosong"
            })

        if not db.query(master_excel).first():
            return JSONResponse(status_code=404, content={
                "status": "error",
                "status_code": 404,
                "message": "Referensi master tidak ditemukan"
            })

        existing_norangka = {row[0] for row in db.query(master_excel.norangka).all()}
        duplikat = [d.norangka for d in data if d.norangka in existing_norangka]
        if duplikat:
            return JSONResponse(status_code=409, content={
                "status": "error",
                "status_code": 409,
                "message": "Data duplikat ditemukan",
                "detail": duplikat
            })

        for d in data:
            if not d.norangka or d.norangka.strip() == "":
                return JSONResponse(status_code=400, content={
                    "status": "error",
                    "status_code": 400,
                    "message": "Nomor rangka tidak boleh kosong"
                })

        records = [
            master_excel(
                norangka=d.norangka,
                nama_stnk=d.nama_stnk,
                kode_tipe=d.kode_tipe,
                tipe=d.tipe,
                kode_model=d.kode_model,
                model=d.model,
                merk=d.merk,
                kode_samsat=d.kode_samsat,
                samsat=d.samsat,
                kode_dealer=d.kode_dealer,
                nama_dealer=d.nama_dealer,
                kode_group=d.kode_group,
                group_perusahaan=d.group_perusahaan,
                tgl_mohon_stnk=d.tgl_mohon_stnk,
                tgl_simpan=d.tgl_simpan,
                nama_pt=d.nama_pt,
                kode_cabang=d.kode_cabang
            ) for d in data
        ]

        db.bulk_save_objects(records)
        db.commit()

        return {
            "message": "Data berhasil disimpan",
            "count": len(records),
            "status_code": 200
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "error",
            "status_code": 500,
            "message": "Terjadi kesalahan pada server",
            "detail": str(e)
        })
