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


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/stnk-data/")
def get_all_stnk_data():
    db = SessionLocal()
    try:
        stnk_entries = db.query(STNKData).all()
        data = []

        for entry in stnk_entries:
            entry_dict = entry.__dict__.copy()
            entry_dict.pop("_sa_instance_state", None)

            # Tambahkan image_url jika file_path tersedia
            if entry.path:
                relative_path = os.path.relpath(entry.path, start="app")  # contoh: storage/batch_xxx/namafile.jpg
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
def get_ktp_data_with_corrections():
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
    nomor_rangka: str
    details: Optional[STNKDetail] = None

@app.post("/save-stnk-data/")
async def save_data_stnk(request: STNKSaveRequest):
    db = SessionLocal()
    
    try:
        print(f"Received request: {request}")
        
        if not request.nomor_rangka or request.nomor_rangka.strip() in ["", "-"]:
            raise HTTPException(status_code=400, detail="Nomor rangka cannot be empty")
        
        existing = db.query(STNKData).filter(
            STNKData.nomor_rangka == request.nomor_rangka.strip()
        ).first()
        
        if existing:
            return {
                "status": "error",
                "message": "The Frame Number already exists in the database"
            }

        jumlah_value = request.details.jumlah if request.details else None
        
        # Rename file logic
        old_path = request.path  # Contoh: 'app/storage/batch_abc/stnk1.jpg'
        old_dir = os.path.dirname(old_path)
        ext = os.path.splitext(request.filename)[1]  # Ambil ekstensi (misalnya: .jpg)
        new_filename = f"{request.nomor_rangka.strip()}{ext}"
        new_path = os.path.join(old_dir, new_filename)

        try:
            os.rename(old_path, new_path)
            print(f"File renamed from {old_path} to {new_path}")
        except FileNotFoundError:
            print(f"[WARNING] File tidak ditemukan untuk rename: {old_path}")
        except Exception as e:
            print(f"[ERROR] Rename file gagal: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Gagal mengganti nama file: {e}")

        # Simpan ke database dengan nama file baru
        stnk_entry = STNKData(
            file=new_filename,
            path=new_path,
            nomor_rangka=request.nomor_rangka.strip(),
            jumlah=jumlah_value
        )
        
        db.add(stnk_entry)
        db.commit()
        db.refresh(stnk_entry)

        return {
            "status": "success",
            "message": "STNK data saved successfully",
            "data": {
                "id": stnk_entry.id,
                "filename": stnk_entry.file,
                "nomor_rangka": stnk_entry.nomor_rangka,
                "jumlah": stnk_entry.jumlah,
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
    stnk_id: int = Path(..., description="ID data STNK yang ingin diperbarui"),
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