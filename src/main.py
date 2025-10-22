from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Request
import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator, Field, AliasChoices
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
from datetime import datetime, date, timezone

from .database import Base, engine, get_db
from .models import CatSighting as CatSightingModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import text as sql_text
import io
import csv
import uuid
import pathlib

load_dotenv()

# Create tables if they don't exist (simple start; migrations recommended later)
Base.metadata.create_all(bind=engine)
# Lightweight migration: ensure spotted_at column exists
try:
    with engine.begin() as conn:
        conn.execute(sql_text("ALTER TABLE cat_sightings ADD COLUMN IF NOT EXISTS spotted_at TIMESTAMPTZ"))
except Exception:
    # Best-effort; avoid crashing app if migration fails in a non-Postgres env
    pass

app = FastAPI(title="NYC Cat Tracker API")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cat-api")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static uploads directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Pydantic models for request/response
class CatSightingCreate(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None
    description: Optional[str] = None
    # Accept both snake_case and camelCase
    cat_name: Optional[str] = Field(default=None, validation_alias=AliasChoices("cat_name", "catName"))
    image_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("image_url", "imageUrl"))
    source: Optional[str] = "map"
    spotted_at: Optional[datetime] = Field(default=None, validation_alias=AliasChoices("spotted_at", "spottedAt"))

    @field_validator("spotted_at", mode="before")
    @classmethod
    def _parse_spotted_at(cls, v: Optional[object]) -> Optional[datetime]:
        if v is None:
            return None
        if isinstance(v, datetime):
            # Ensure timezone-aware; default to UTC if naive
            return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if isinstance(v, (int, float)):
            # Treat as unix seconds
            try:
                return datetime.fromtimestamp(float(v), tz=timezone.utc)
            except Exception:
                return None
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            # Handle trailing Z (UTC)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            # Try full datetime first
            try:
                dt = datetime.fromisoformat(s)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
            # Try date-only: YYYY-MM-DD
            try:
                d = date.fromisoformat(s)
                return datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc)
            except Exception:
                return None
        return None

class CatSightingResponse(BaseModel):
    id: int
    lat: float
    lng: float
    address: Optional[str] = None
    description: Optional[str] = None
    cat_name: Optional[str] = None
    image_url: Optional[str] = None
    source: str
    spotted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ReportsSummaryResponse(BaseModel):
    total: int
    by_source: Dict[str, int]
    per_day: List[Dict[str, Any]]
    start: datetime
    end: datetime

@app.get("/")
def read_root():
    return {"message": "NYC Cat Tracker API", "version": "1.0.0"}

@app.get("/api/cats", response_model=List[CatSightingResponse])
def get_cat_sightings(db: Session = Depends(get_db)):
    rows = db.query(CatSightingModel).order_by(CatSightingModel.created_at.desc()).all()
    return rows

@app.post("/api/cats", response_model=CatSightingResponse, status_code=201)
async def create_cat_sighting(sighting: CatSightingCreate, request: Request, db: Session = Depends(get_db)):
    # Default spotted_at to now if omitted
    spotted_at = sighting.spotted_at or datetime.now(timezone.utc)
    # Prefer explicit body keys as a last resort to capture any naming variations
    try:
        raw = await request.json()
    except Exception:
        raw = {}
    # Try multiple variants for cat name
    cat_name_val = sighting.cat_name or raw.get("cat_name") or raw.get("catName")
    if cat_name_val is None and isinstance(raw, dict):
        for k, v in raw.items():
            try:
                nk = str(k).replace("_", "").lower()
            except Exception:
                continue
            if nk == "catname" or nk.endswith("catname"):
                cat_name_val = v
                break

    logger.info("POST /api/cats body=%s parsed.cat_name=%s chosen=%s", raw, sighting.cat_name, cat_name_val)

    row = CatSightingModel(
        lat=sighting.lat,
        lng=sighting.lng,
        address=sighting.address,
        description=sighting.description,
        cat_name=cat_name_val,
        image_url=sighting.image_url,
        source=sighting.source or "map",
        spotted_at=spotted_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("Saved sighting id=%s cat_name=%s desc=%s", row.id, row.cat_name, row.description)
    return row

@app.get("/api/cats/{sighting_id}", response_model=CatSightingResponse)
def get_cat_sighting(sighting_id: int, db: Session = Depends(get_db)):
    row = db.query(CatSightingModel).filter(CatSightingModel.id == sighting_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Cat sighting not found")
    return row

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")
    ext = pathlib.Path(file.filename or "").suffix.lower()
    # Basic extension allowlist (optional)
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        ext = ".jpg"
    name = f"{uuid.uuid4().hex}{ext}"
    dest_path = pathlib.Path(UPLOAD_DIR) / name
    try:
        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    finally:
        await file.aclose()
    return {"url": f"/uploads/{name}"}

def _parse_date_range(start: Optional[str], end: Optional[str]) -> (datetime, datetime):
    """Parse ISO date strings (YYYY-MM-DD) into inclusive datetime bounds in local time.
    If missing, default to last 30 days.
    """
    now = datetime.now()
    if not end:
        end_dt = now
    else:
        # end of day
        end_dt = datetime.fromisoformat(end)
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    if not start:
        start_dt = datetime.fromtimestamp(end_dt.timestamp() - 29 * 24 * 3600)
    else:
        start_dt = datetime.fromisoformat(start)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_dt, end_dt

@app.get("/api/reports/summary", response_model=ReportsSummaryResponse)
def get_reports_summary(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    start_dt, end_dt = _parse_date_range(start, end)

    base_q = db.query(CatSightingModel).filter(
        CatSightingModel.created_at >= start_dt,
        CatSightingModel.created_at <= end_dt,
    )

    total = base_q.count()

    # by source
    src_rows = (
        db.query(CatSightingModel.source, func.count(CatSightingModel.id))
        .filter(
            CatSightingModel.created_at >= start_dt,
            CatSightingModel.created_at <= end_dt,
        )
        .group_by(CatSightingModel.source)
        .all()
    )
    by_source: Dict[str, int] = {s or "unknown": c for s, c in src_rows}

    # per day counts (using date(created_at))
    day_rows = (
        db.query(func.date(CatSightingModel.created_at), func.count(CatSightingModel.id))
        .filter(
            CatSightingModel.created_at >= start_dt,
            CatSightingModel.created_at <= end_dt,
        )
        .group_by(func.date(CatSightingModel.created_at))
        .order_by(func.date(CatSightingModel.created_at))
        .all()
    )
    per_day = [
        {"date": str(d), "count": count}
        for d, count in day_rows
    ]

    return ReportsSummaryResponse(
        total=total,
        by_source=by_source,
        per_day=per_day,
        start=start_dt,
        end=end_dt,
    )

@app.get("/api/reports/export")
def export_reports_csv(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    start_dt, end_dt = _parse_date_range(start, end)

    rows: List[CatSightingModel] = (
        db.query(CatSightingModel)
        .filter(
            CatSightingModel.created_at >= start_dt,
            CatSightingModel.created_at <= end_dt,
        )
        .order_by(CatSightingModel.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "lat",
        "lng",
        "address",
        "description",
        "cat_name",
        "image_url",
        "source",
        "spotted_at",
        "created_at",
        "updated_at",
    ])
    for r in rows:
        writer.writerow([
            r.id,
            r.lat,
            r.lng,
            r.address or "",
            r.description or "",
            r.cat_name or "",
            r.image_url or "",
            r.source,
            r.spotted_at.isoformat() if getattr(r, "spotted_at", None) else "",
            r.created_at.isoformat() if r.created_at else "",
            r.updated_at.isoformat() if r.updated_at else "",
        ])

    output.seek(0)
    filename = f"cat_sightings_{start_dt.date()}_to_{end_dt.date()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
