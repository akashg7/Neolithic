from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'farmer', 'buyer', 'fpo_admin'
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry('POINT', srid=4326), nullable=True, index=True)
    preferred_language = Column(String(10), default="en")
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    farmer_profile = relationship("Farmer", back_populates="user", uselist=False)
    buyer_profile = relationship("Buyer", back_populates="user", uselist=False)


class Farmer(Base):
    __tablename__ = "farmers"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=True)

    user = relationship("User", back_populates="farmer_profile")
    fpo = relationship("FPO", back_populates="farmers")


class Buyer(Base):
    __tablename__ = "buyers"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    company_name = Column(String(200), nullable=True)
    verified_status = Column(Boolean, default=False)

    user = relationship("User", back_populates="buyer_profile")
