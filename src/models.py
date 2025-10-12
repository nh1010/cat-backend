from sqlalchemy import Column, Integer, Float, String, DateTime, CheckConstraint
from sqlalchemy.sql import func
from .database import Base

class CatSighting(Base):
    __tablename__ = "cat_sightings"

    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    description = Column(String, nullable=True)
    cat_name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    source = Column(String, nullable=False, default="map")  # 'map' | 'address'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("source in ('map','address')", name="cat_sightings_source_check"),
    )

