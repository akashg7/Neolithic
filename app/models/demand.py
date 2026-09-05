from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class BuyerDemand(Base):
    __tablename__ = "buyer_demand"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    crop = Column(String(100), nullable=False)
    desired_qty_kg = Column(Integer, nullable=False)
    desired_grade = Column(String(5), nullable=True)
    max_price_paise_per_qtl = Column(Integer, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    source = Column(String(10), default="real")  # 'real' or 'demo'
