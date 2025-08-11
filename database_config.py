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
    origin = Column(String(100), nullable=False)         # scraped origin
    departure_time = Column(DateTime, nullable=False)    # Changed to DateTime
    destination = Column(String(100), nullable=False)    # scraped destination
    arrival_time = Column(DateTime, nullable=False)      # Changed to DateTime
    duration = Column(String(50), nullable=False)
    distance = Column(String(50), nullable=True)
    halts = Column(String(100), nullable=True)
    origin_code = Column(String(10), nullable=True)
    destination_code = Column(String(10), nullable=True)
    origin_query = Column(String(100), nullable=False)     # Added - from request
    destination_query = Column(String(100), nullable=False) # Added - from request
    created_at = Column(DateTime, default=datetime.utcnow)
    # Removed search_date column

    seat_availability = relationship("SeatAvailability", back_populates="schedule", cascade="all, delete-orphan")

class SeatAvailability(Base):
    __tablename__ = "seat_availability"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("transport_schedules.id"), nullable=False)
    class_name = Column(String(100), nullable=False)
    class_description = Column(String(200), nullable=True)
    status = Column(String(100), nullable=False)
    price = Column(String(20), nullable=False)

    schedule = relationship("TransportSchedules", back_populates="seat_availability")

class Bookings(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(100), nullable=False)
    schedule_id = Column(Integer, ForeignKey("transport_schedules.id"), nullable=False)
    booking_status = Column(String(20), default="confirmed")  # confirmed, cancelled
    booking_date = Column(DateTime, default=datetime.utcnow)

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

def clear_all_tables():
    """Clear all data from tables - for development use only"""
    db = SessionLocal()
    try:
        # Delete in order to respect foreign key constraints
        db.query(SeatAvailability).delete()
        db.query(Bookings).delete()
        db.query(TransportSchedules).delete()
        db.commit()
        print("All table data cleared successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error clearing tables: {e}")
        raise
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