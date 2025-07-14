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
from app.db.model import User, STNKData, STNKFieldCorrection, stpm_orlap, glbm_samsat, glbm_wilayah_cakupan , glbm_wilayah , Detail_otorirasi_samsat, otorirasi_samsat,RoleEnum,Role,glbm_brand,glbm_pt
from app.db.database import engine
Base.metadata.create_all(bind=engine)  # Ganti path sesuai tempat kamu menyimpan enum-nya
from app.utils.auth import create_access_token
from datetime import datetime, timedelta
from app.middleware.login import LoginMiddleware
app.add_middleware(LoginMiddleware)
from app.utils.auth import require_role
from app.db.database import get_db
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, joinedload
from app.utils.auth import get_current_user 
import pandas as pd





# Function untuk mengembalikan semua user
def get_all_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        result = []

        for user in users:
            user_data = {
                "id": user.id,
                "username": user.username,
                "gmail": user.gmail,
                "role": user.role.role if user.role else None,
                "otorisasi": []
            }

            # Ambil semua otorisasi user
            otorisasi_list = db.query(otorirasi_samsat).filter(
                otorirasi_samsat.user_id == user.id
            ).all()

            for otor in otorisasi_list:
                detail = db.query(Detail_otorirasi_samsat).filter(
                    Detail_otorirasi_samsat.id == otor.detail_otorirasi_samsat_id
                ).first()

                if not detail:
                    continue

                user_data["otorisasi"].append({
                    "brand_id": detail.glbm_brand_id,
                    "pt_id": detail.glbm_pt_id,
                    "samsat_id": detail.glbm_samsat_id,
                    "wilayah_id": detail.wilayah_id,
                    "wilayah_cakupan_id": detail.wilayah_cakupan_id
                })

            result.append(user_data)

        return result
    finally:
        db.close()


# Endpoint untuk mengirim hasil function dictionary
@app.get("/users")
def read_users(current_user=Depends(require_role(RoleEnum.CAO,RoleEnum.ADMIN, RoleEnum.SUPERADMIN))):
    return {"data": get_all_users()}


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
    gmail: str
    password: str
    role_id: int
    nama_lengkap: str
    nomor_telepon: str
    glbm_brand_ids: List[int]  # ⬅️ List brand
    glbm_pt_id: int
    glbm_samsat_id: int


@app.post("/register")
def register(data: RegisterData, db: Session = Depends(get_db)):
    # Validasi awal: field wajib
    missing_fields = []
    if not data.username:
        missing_fields.append("username")
    if not data.gmail:
        missing_fields.append("gmail")
    if not data.password:
        missing_fields.append("password")
    if not data.role_id:
        missing_fields.append("role_id")
    if not data.nama_lengkap:
        missing_fields.append("nama_lengkap")
    if not data.nomor_telepon:
        missing_fields.append("nomor_telepon")
    if not data.glbm_samsat_id:
        missing_fields.append("glbm_samsat_id")
    if not data.glbm_pt_id:
        missing_fields.append("glbm_pt_id")
    if not data.glbm_brand_ids or len(data.glbm_brand_ids) == 0:
        missing_fields.append("glbm_brand_ids")

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Field berikut wajib diisi: {', '.join(missing_fields)}"
        )

    # Cek username & gmail
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")
    if db.query(User).filter(User.gmail == data.gmail).first():
        raise HTTPException(status_code=400, detail="Gmail sudah terdaftar")

    # Cek role
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan")

    # Validasi samsat
    samsat = db.query(glbm_samsat).filter(glbm_samsat.id == data.glbm_samsat_id).first()
    if not samsat:
        raise HTTPException(status_code=404, detail="Samsat tidak ditemukan")

    wilayah_cakupan_id = samsat.wilayah_cakupan_id
    wilayah_id = samsat.wilayah_id

    # Mulai transaksi DB
    try:
        # Buat orlap
        new_orlap = stpm_orlap(
            nama_lengkap=data.nama_lengkap,
            nomor_telepon=data.nomor_telepon
        )
        db.add(new_orlap)
        db.flush()  # gunakan flush untuk dapat ID tanpa commit

        # Buat user
        new_user = User(
            username=data.username,
            gmail=data.gmail,
            hashed_password=data.password,
            role_id=role.id,
            stpm_orlap_id=new_orlap.id
        )
        db.add(new_user)
        db.flush()

        otorisasi_list = []
        for brand_id in data.glbm_brand_ids:
            detail = Detail_otorirasi_samsat(
                glbm_samsat_id=data.glbm_samsat_id,
                glbm_brand_id=brand_id,
                glbm_pt_id=data.glbm_pt_id,
                wilayah_cakupan_id=wilayah_cakupan_id,
                wilayah_id=wilayah_id
            )
            db.add(detail)
            db.flush()

            otorisasi = otorirasi_samsat(
                user_id=new_user.id,
                detail_otorirasi_samsat_id=detail.id
            )
            db.add(otorisasi)
            db.flush()

            otorisasi_list.append({
                "detail_otorirasi_samsat_id": detail.id,
                "glbm_samsat_id": data.glbm_samsat_id,
                "glbm_brand_id": brand_id,
                "glbm_pt_id": data.glbm_pt_id
            })

        db.commit()

        return {
            "message": "Registrasi dan Otorisasi berhasil",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "gmail": new_user.gmail,
                "role": role.role.value,
                "nama_lengkap": new_orlap.nama_lengkap,
                "nomor_telepon": new_orlap.nomor_telepon
            },
            "otorisasi": otorisasi_list
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registrasi gagal: {str(e)}")

class OtorisasiItem(BaseModel):
    brand_id: int
    pt_id: int

class UpdateUserData(BaseModel):
    username: Optional[str] = None
    gmail: Optional[EmailStr] = None
    role_id: Optional[int] = None
    otorisasi: Optional[List[OtorisasiItem]] = None

@app.put("/update-user/{user_id}")
def update_user(
    user_id: int,
    data: UpdateUserData,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
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

        # === Update Otorisasi: brand & pt ===
        if data.otorisasi:
            otorisasi_list = db.query(otorirasi_samsat).filter(
                otorirasi_samsat.user_id == user.id
            ).all()

            for i, otor in enumerate(otorisasi_list):
                detail = db.query(Detail_otorirasi_samsat).filter(
                    Detail_otorirasi_samsat.id == otor.detail_otorirasi_samsat_id
                ).first()

                if not detail or i >= len(data.otorisasi):
                    continue

                otor_data = data.otorisasi[i]

                detail.glbm_brand_id = otor_data.brand_id
                detail.glbm_pt_id = otor_data.pt_id

                db.add(detail)

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
def get_user_profile(
    current_user : dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user_id = int(current_user.get("sub"))  # Ambil user_id dari token
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")

        return {
            "id": user.id,
            "username": user.username,
            "gmail": user.gmail,
            "nama_lengkap": user.stpm_orlap.nama_lengkap,
            "nomor_telepon": user.stpm_orlap.nomor_telepon,
            "role": user.role.role.value
        }
    except Exception as e:
        print("ERROR GET USER PROFILE:", str(e))
        raise HTTPException(status_code=500, detail="Terjadi kesalahan saat mengambil profil user")

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


@app.get("/detail-otorirasi-samsat")
def get_detail_otorirasi_samsat(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        # Ambil seluruh data cakupan wilayah beserta relasinya
        cakupan_list = db.query(glbm_wilayah_cakupan).options(
            joinedload(glbm_wilayah_cakupan.wilayah),
            joinedload(glbm_wilayah_cakupan.detail_otorirasi_samsat).joinedload(Detail_otorirasi_samsat.glbm_samsat)
        ).all()

        data = []
        for cakupan in cakupan_list:
            wilayah = cakupan.wilayah
            data.append({
                "id_wilayah_cakupan": cakupan.id,
                "nama_wilayah_cakupan": cakupan.nama_wilayah,
                "wilayah_induk": wilayah.nama_wilayah if wilayah else None,
                "detail_otorirasi_samsat": [
                    {
                        "id": d.id,
                        "glbm_samsat_id": d.glbm_samsat_id,
                        "glbm_samsat_nama": d.glbm_samsat.nama_samsat if d.glbm_samsat else None,
                    }
                    for d in cakupan.detail_otorirasi_samsat
                ]
            })

        return {"status": "success", "data": data}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/otorirasi-samsat")
def get_otorirasi_samsat(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.CAO, RoleEnum.ADMIN, RoleEnum.SUPERADMIN))
):
    try:
        otorisasi_list = db.query(otorirasi_samsat).options(
            joinedload(otorirasi_samsat.user),
            joinedload(otorirasi_samsat.detail_otorirasi_samsat)
                .joinedload(Detail_otorirasi_samsat.glbm_samsat),
            joinedload(otorirasi_samsat.detail_otorirasi_samsat)
                .joinedload(Detail_otorirasi_samsat.detail_wilayah_cakupan)
                .joinedload(glbm_wilayah_cakupan.wilayah)
        ).all()

        data = []
        for item in otorisasi_list:
            detail = item.detail_otorirasi_samsat
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


class OtorisasiRequest(BaseModel):
    user_id: int
    detail_otorirasi_samsat_id: Optional[int] = None
    detail_otorirasi_samsat_ids: Optional[List[int]] = None

@app.post("/add-otorisasi-samsat")
def add_otorisasi_samsat(
    request: OtorisasiRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(RoleEnum.ADMIN, RoleEnum.CAO, RoleEnum.SUPERADMIN))
):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # Mode Multiple
    if request.detail_otorirasi_samsat_ids:
        results = []
        for detail_id in request.detail_otorirasi_samsat_ids:
            detail = db.query(Detail_otorirasi_samsat).filter_by(id=detail_id).first()
            if not detail:
                continue  # Lewatkan kalau tidak ditemukan

            existing = db.query(otorirasi_samsat).filter_by(
                user_id=request.user_id,
                detail_otorirasi_samsat_id=detail_id
            ).first()
            if existing:
                continue

            new_otorisasi = otorirasi_samsat(
                user_id=request.user_id,
                detail_otorirasi_samsat_id=detail_id
            )
            db.add(new_otorisasi)
            db.commit()
            db.refresh(new_otorisasi)

            results.append({
                "user_id": new_otorisasi.user_id,
                "detail_otorirasi_samsat_id": new_otorisasi.detail_otorirasi_samsat_id
            })

        return {
            "status": "success",
            "message": f"{len(results)} otorisasi berhasil ditambahkan",
            "data": results
        }

    # Mode Single
    elif request.detail_otorirasi_samsat_id:
        detail = db.query(Detail_otorirasi_samsat).filter_by(id=request.detail_otorirasi_samsat_id).first()
        if not detail:
            raise HTTPException(status_code=404, detail="Detail otorisasi tidak ditemukan")

        existing = db.query(otorirasi_samsat).filter_by(
            user_id=request.user_id,
            detail_otorirasi_samsat_id=request.detail_otorirasi_samsat_id
        ).first()
        if existing:
            return {
                "status": "error",
                "message": "User sudah memiliki otorisasi ini"
            }

        new_otorisasi = otorirasi_samsat(
            user_id=request.user_id,
            detail_otorirasi_samsat_id=request.detail_otorirasi_samsat_id
        )
        db.add(new_otorisasi)
        db.commit()
        db.refresh(new_otorisasi)

        return {
            "status": "success",
            "message": "Otorisasi berhasil ditambahkan",
            "data": {
                "user_id": new_otorisasi.user_id,
                "detail_otorirasi_samsat_id": new_otorisasi.detail_otorirasi_samsat_id
            }
        }

    # Tidak ada field yang dikirim
    else:
        raise HTTPException(
            status_code=400,
            detail="Harus menyertakan salah satu dari 'detail_otorirasi_samsat_id' atau 'detail_otorirasi_samsat_ids'"
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

@app.post("/import-excel/")
async def import_excel(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # baca seluruh isi file sebagai bytes
        content = await file.read()
        excel_data = io.BytesIO(content)

        # baca file excel dari stream
        df = pd.read_excel(excel_data, engine="openpyxl", dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error membaca file: {e}")

    required_cols = ["norangka", "kodesamsat", "namaPT", "merk"]
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Kolom '{col}' tidak ditemukan dalam Excel")

    created = 0
    for idx, row in df.iterrows():
        # cari atau buat glbm_samsat
        samsat = db.query(glbm_samsat).filter_by(kode_samsat=row["kodesamsat"]).first()
        if not samsat:
            raise HTTPException(status_code=400, detail=f"Samsat code '{row['kodesamsat']}' baris {idx+2} tidak valid")

        # cari atau buat PT dan Brand jika diperlukan
        pt = db.query(glbm_pt).filter_by(nama_pt=row["namaPT"]).first()
        if not pt:
            pt = glbm_pt(nama_pt=row["namaPT"], kode_pt=row.get("kode_cabang", row["namaPT"]))
            db.add(pt)
            db.commit()
            db.refresh(pt)

        brand = db.query(glbm_brand).filter_by(nama_brand=row["merk"]).first()
        if not brand:
            brand = glbm_brand(nama_brand=row["merk"], kode_brand=row["merk"][:10].upper())
            db.add(brand)
            db.commit()
            db.refresh(brand)

        stnk = STNKData(
            user_id=user.id,
            glbm_samsat_id=samsat.id,
            nomor_rangka=row["norangka"],
            kode_samsat=row["kode_samsat"],
            nama_pt=row["namaPT"],
            nama_brand=row["merk"],
        )
        db.add(stnk)
        created += 1

    db.commit()
    return {"message": f"Berhasil membuat {created} entry STNKData"}

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
@app.get("/stnk-data/")
def get_all_stnk_data(current_user: dict = Depends(get_current_user)):    
    db = SessionLocal()
    try:
        role = current_user.get("role")
        user_id = int(current_user.get("sub"))  # user_id dari token

        query = db.query(STNKData)

        if role == "superadmin":
            # Superadmin akses semua data
            stnk_entries = query.all()

        elif role == "cao":
            # Ambil data otorisasi user
            otorisasi_query = db.query(Detail_otorirasi_samsat).join(otorirasi_samsat).filter(
                otorirasi_samsat.user_id == user_id
            )

            wilayah_cakupan_ids = [row.wilayah_cakupan_id for row in otorisasi_query]
            brand_names = [row.glbm_brand.nama_brand for row in otorisasi_query if row.glbm_brand]
            pt_names = [row.glbm_pt.nama_pt for row in otorisasi_query if row.glbm_pt]

            # Ambil samsat sesuai wilayah_cakupan
            samsat_ids = db.query(glbm_samsat.id).filter(
                glbm_samsat.wilayah_cakupan_id.in_(wilayah_cakupan_ids)
            ).all()
            samsat_ids = [id for (id,) in samsat_ids]

            # Filter STNK berdasarkan samsat_id, nama_brand, dan nama_pt
            filters = [STNKData.glbm_samsat_id.in_(samsat_ids)]
            if brand_names:
                filters.append(STNKData.nama_brand.in_(brand_names))
            if pt_names:
                filters.append(STNKData.nama_pt.in_(pt_names))

            stnk_entries = query.filter(*filters).all()

        elif role == "admin":
            # Ambil data otorisasi admin
            otorisasi_query = db.query(Detail_otorirasi_samsat).join(otorirasi_samsat).filter(
                otorirasi_samsat.user_id == user_id
            )

            wilayah_ids = [row.wilayah_id for row in otorisasi_query]
            pt_names = [row.glbm_pt.nama_pt for row in otorisasi_query if row.glbm_pt]

            samsat_ids = db.query(glbm_samsat.id).filter(
                glbm_samsat.wilayah_id.in_(wilayah_ids)
            ).all()
            samsat_ids = [id for (id,) in samsat_ids]

            filters = [STNKData.glbm_samsat_id.in_(samsat_ids)]
            if pt_names:
                filters.append(STNKData.nama_pt.in_(pt_names))

            stnk_entries = query.filter(*filters).all()

        else:
            return {
                "status": "forbidden",
                "message": "Anda tidak memiliki akses"
            }

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
async def upload_stnk_batch(files: List[UploadFile] = File(..., description="Unggah hingga 10 gambar STNK untuk diproses.")):
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
            partial(run_batch_processing, batch_directory=batch_dir, pipeline_path=ml_models["ocr_model"], candidate_count=10)
        )
        
        # 5. Kembalikan hasil dari fungsi pemrosesan
        return processing_results

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
    filename: str
    path: str
    user_id: int
    glbm_samsat_id: int
    nomor_rangka: str
    details: Optional[STNKDetail] = None
from sqlalchemy import text


@app.post("/save-stnk-data/")
async def save_data_stnk(request: STNKSaveRequest):
    db: Session = SessionLocal()
    
    try:
        print(f"Received request: {request}")
        
        if not request.nomor_rangka or request.nomor_rangka.strip() in ["", "-"]:
            raise HTTPException(status_code=400, detail="Nomor rangka tidak boleh kosong")
        
        # Cek apakah nomor rangka sudah ada
        existing = db.query(STNKData).filter(
            STNKData.nomor_rangka == request.nomor_rangka.strip()
        ).first()
        
        if existing:
            return {
                "status": "error",
                "message": "Nomor rangka sudah ada di database"
            }

        # Ambil data samsat untuk ambil kode_samsat
        samsat = db.query(glbm_samsat).filter(glbm_samsat.id == request.glbm_samsat_id).first()
        if not samsat:
            raise HTTPException(status_code=404, detail="Data Samsat tidak ditemukan")

        # Rename file
        old_path = request.path
        old_dir = os.path.dirname(old_path)
        ext = os.path.splitext(request.filename)[1]
        new_filename = f"{request.nomor_rangka.strip()}{ext}"
        new_path = os.path.join(old_dir, new_filename)

        try:
            os.rename(old_path, new_path)
            print(f"File renamed from {old_path} to {new_path}")
        except FileNotFoundError:
            print(f"[WARNING] File tidak ditemukan: {old_path}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal mengganti nama file: {e}")

        # Ambil jumlah dari detail (jika ada)
        jumlah_value = request.details.jumlah if request.details else None

        # Ambil nama_brand dan nama_pt via LEFT JOIN dari detail_otorirasi_samsat
        nama_brand = None
        nama_pt = None

        sql = text("""
            SELECT 
                b.nama_brand, p.nama_pt
            FROM detail_otorirasi_samsat d
            LEFT JOIN glbm_brand b ON d.glbm_brand_id = b.id
            LEFT JOIN glbm_pt p ON d.glbm_pt_id = p.id
            WHERE d.glbm_samsat_id = :samsat_id
            LIMIT 1
        """)
        result = db.execute(sql, {"samsat_id": request.glbm_samsat_id}).fetchone()
        if result:
            nama_brand = result[0]
            nama_pt = result[1]

        # Simpan ke database
        stnk_entry = STNKData(
            file=new_filename,
            path=new_path,
            user_id=request.user_id,
            glbm_samsat_id=request.glbm_samsat_id,
            kode_samsat=samsat.kode_samsat,
            nomor_rangka=request.nomor_rangka.strip(),
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
                "glbm_samsat_id": stnk_entry.glbm_samsat_id,
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