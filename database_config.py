import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://ticketingmaster:ticketferric@localhost:5432/ticketing_db"
)

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class TransportSchedules(Base):
    __tablename__ = "transport_schedules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transport_mode = Column(String(50), nullable=False)  # train, bus, flight
    transport_id = Column(String(20), nullable=False)    # train number, bus id, etc
    transport_name = Column(String(200), nullable=False) # train name, bus name, etc
    origin = Column(String(100), nullable=False)
    departure_time = Column(String(20), nullable=False)
    destination = Column(String(100), nullable=False)
    arrival_time = Column(String(20), nullable=False)
    duration = Column(String(50), nullable=False)
    distance = Column(String(50), nullable=False)
    halts = Column(String(100), nullable=False)
    origin_code = Column(String(10), nullable=True)
    destination_code = Column(String(10), nullable=True)
    search_date = Column(String(20), nullable=False)  # Date for which this schedule was searched
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with seat availability
    seat_availability = relationship("SeatAvailability", back_populates="schedule", cascade="all, delete-orphan")

class SeatAvailability(Base):
    __tablename__ = "seat_availability"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("transport_schedules.id"), nullable=False)
    class_name = Column(String(100), nullable=False)
    class_description = Column(String(200), nullable=True)
    status = Column(String(100), nullable=False)
    price = Column(String(20), nullable=False)
    
    # Relationship back to schedule
    schedule = relationship("TransportSchedules", back_populates="seat_availability")

class Bookings(Base):
    __tablename__ = "bookings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(100), nullable=False)
    schedule_id = Column(Integer, ForeignKey("transport_schedules.id"), nullable=False)
    # seat_class = Column(String(100), nullable=True)
    booking_status = Column(String(20), default="confirmed")  # confirmed, cancelled
    booking_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with schedule
    schedule = relationship("TransportSchedules")

# Database functions
def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database with tables"""
    try:
        create_tables()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise

if __name__ == "__main__":
    # Create tables if running directly
    init_database()