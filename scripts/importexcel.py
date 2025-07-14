from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import pandas as pd
from app.db.database import get_db, SessionLocal
from app.db.model import User  # Contoh model

app = FastAPI()

