'''
    Import Lib Untuk Utility
'''

from typing import List, Optional
from openai import BaseModel
import setuptools
import uuid
import shutil
import os


'''
    Import Lib Untuk API
'''
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException

'''
    Import Lib Untuk Utility
'''
from app.pipeline.extract_nomor_rangka import extract_nomor_rangka_fast
from paddlex import create_pipeline

'''
    Import DB
'''
from app.db.database import Base, engine
from app.db.model import STNKData
from app.db.model import STNKFieldCorrection
from app.db.database import SessionLocal


'''
    Init Instance [app, middleware, pipeline ocr, DB]
'''
app = FastAPI()
app.include_router(prefix="/api/v1")

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
    "https://8jnbbt04-5173.asse.devtunnels.ms/upload-stnk"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi pipeline OCR sekali saat aplikasi dimulai
pipeline = create_pipeline(pipeline="OCR")

@app.get("/")
def read_root():
    return {"Hello": "World"}



'''
    OCR API
'''
@app.get("/stnk-data/")
def get_all_stnk_data():
    db = SessionLocal()
    try:
        stnk_entries = db.query(STNKData).all()
        data = []
        for entry in stnk_entries:
            entry_dict = entry.__dict__.copy()
            entry_dict.pop("_sa_instance_state", None)
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

# @app.post("/upload-stnk/")
# async def upload_image(file: UploadFile = File(...)):
#     temp_path = f"temp_{file.filename}"
#     with open(temp_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     db = SessionLocal()
#     try:
#         output = pipeline.predict(
#             input=temp_path,
#             use_doc_orientation_classify=False,
#             use_doc_unwarping=False,
#             use_textline_orientation=False,
#         )

#         nomor_rangka, info, texts = extract_nomor_rangka_fast(output)

#         if nomor_rangka and nomor_rangka.strip() not in ["", "-"]:
#             existing = db.query(STNKData).filter(STNKData.nomor_rangka == nomor_rangka).first()
#             if existing:
#                 return {
#                     "status": "error",
#                     "message": "The Frame Number already exists in the database"
#                 }

#         stnk_entry = STNKData(file=file.filename, nomor_rangka=nomor_rangka)
#         db.add(stnk_entry)
#         db.commit()
#         db.refresh(stnk_entry)

#         return {
#             "filename": file.filename,
#             "nomor_rangka": nomor_rangka,
#             "full_text" : texts,
#             'info' : info
#         }

#     except Exception as e:
#         return {"status": "error", "message": str(e)}

#     finally:
#         db.close()
#         if os.path.exists(temp_path):
#             os.remove(temp_path)

# Pydantic model for save request
class STNKSaveRequest(BaseModel):
    filename: str
    nomor_rangka: str
    corrected: Optional[bool] = False
    original_nomor_rangka: Optional[str] = None

# Endpoint 1: Extract data only (no database save)
@app.post("/upload-stnk/")
async def upload_stnk(file: UploadFile = File(...)):
    """
    Extract data from STNK image without saving to database
    Returns the extracted information for user review
    """
    temp_path = f"temp_{file.filename}"
    
    try:
        # Save uploaded file temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the image using your pipeline
        output = pipeline.predict(
            input=temp_path,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        
        # Extract nomor rangka and other information
        nomor_rangka, info, texts = extract_nomor_rangka_fast(output)
        
        # Return extracted data without saving
        return {
            "status": "success",
            "filename": file.filename,
            "nomor_rangka": nomor_rangka,
            "full_text": texts,
            "info": info,
            "message": "Data extracted successfully. Please review and confirm."
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error extracting data: {str(e)}"
        }
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Endpoint 2: Save confirmed data to database
@app.post("/save-stnk-data/")
async def save_data_stnk(request: STNKSaveRequest):
    """
    Save confirmed STNK data to database
    This endpoint is called after user reviews and confirms the extracted data
    """
    db = SessionLocal()
    
    try:
        print(f"Received request: {request}")  # Debug log
        
        # Validate that nomor_rangka is not empty
        if not request.nomor_rangka or request.nomor_rangka.strip() in ["", "-"]:
            raise HTTPException(
                status_code=400, 
                detail="Nomor rangka cannot be empty"
            )
        
        # Check if nomor_rangka already exists in database
        existing = db.query(STNKData).filter(
            STNKData.nomor_rangka == request.nomor_rangka.strip()
        ).first()
        
        if existing:
            return {
                "status": "error",
                "message": "The Frame Number already exists in the database"
            }
        
        # Create new STNK entry - only using fields that exist in the model
        stnk_entry = STNKData(
            file=request.filename,
            nomor_rangka=request.nomor_rangka.strip()
            # created_at and updated_at will be set automatically by default values
        )
        
        # Save to database
        db.add(stnk_entry)
        db.commit()
        db.refresh(stnk_entry)
        
        print(f"Data saved successfully: {stnk_entry}")  # Debug log
        
        return {
            "status": "success",
            "message": "STNK data saved successfully",
            "id": stnk_entry.id,
            "nomor_rangka": stnk_entry.nomor_rangka,
            "created_at": stnk_entry.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error saving data: {str(e)}")  # Debug log
        return {
            "status": "error",
            "message": f"Error saving data: {str(e)}"
        }
    
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
