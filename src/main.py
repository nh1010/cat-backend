from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from datetime import datetime

from .database import Base, engine, get_db
from .models import CatSighting as CatSightingModel
from sqlalchemy.orm import Session

load_dotenv()

# Create tables if they don't exist (simple start; migrations recommended later)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="NYC Cat Tracker API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class CatSightingCreate(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None
    description: Optional[str] = None
    cat_name: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = "map"

class CatSightingResponse(BaseModel):
    id: int
    lat: float
    lng: float
    address: Optional[str] = None
    description: Optional[str] = None
    cat_name: Optional[str] = None
    image_url: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@app.get("/")
def read_root():
    return {"message": "NYC Cat Tracker API", "version": "1.0.0"}

@app.get("/api/cats", response_model=List[CatSightingResponse])
def get_cat_sightings(db: Session = Depends(get_db)):
    rows = db.query(CatSightingModel).order_by(CatSightingModel.created_at.desc()).all()
    return rows

@app.post("/api/cats", response_model=CatSightingResponse, status_code=201)
def create_cat_sighting(sighting: CatSightingCreate, db: Session = Depends(get_db)):
    row = CatSightingModel(
        lat=sighting.lat,
        lng=sighting.lng,
        address=sighting.address,
        description=sighting.description,
        cat_name=sighting.cat_name,
        image_url=sighting.image_url,
        source=sighting.source or "map",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@app.get("/api/cats/{sighting_id}", response_model=CatSightingResponse)
def get_cat_sighting(sighting_id: int, db: Session = Depends(get_db)):
    row = db.query(CatSightingModel).filter(CatSightingModel.id == sighting_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Cat sighting not found")
    return row

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
