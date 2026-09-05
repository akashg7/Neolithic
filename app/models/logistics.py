from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class LogisticsProvider(Base):
    __tablename__ = "logistics_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False)  # 'storage' or 'transport'
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    capacity_kg = Column(Integer, nullable=True)
    contact = Column(String(50), nullable=True)
    source = Column(String(10), default="demo")  # 'real' or 'demo'
