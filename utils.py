from sqlalchemy.orm import Session
from database_config import Bookings, TransportSchedules, get_db
from schemas import BookingResponse, CancellationResponse
import uuid


def create_booking(user_id: str, schedule_id: int, db: Session = None ,seat_class: str = None,) -> BookingResponse:
    """Create a new booking"""
    
    if db is None:
        db = next(get_db())
    
    try:
        # Check if schedule exists
        schedule = db.query(TransportSchedules).filter(TransportSchedules.id == schedule_id).first()
        
        if not schedule:
            return BookingResponse(
                booking_id="",
                status="error",
                message="Schedule not found"
            )
        
        # Create new booking
        booking_id = str(uuid.uuid4())
        
        new_booking = Bookings(
            id=booking_id,
            user_id=user_id,
            schedule_id=schedule_id,
            # seat_class=seat_class,
            booking_status="confirmed"
        )
        
        db.add(new_booking)
        db.commit()
        
        return BookingResponse(
            booking_id=booking_id,
            status="success",
            message=f"Booking confirmed for {schedule.transport_name} ({schedule.transport_id}) from {schedule.origin} to {schedule.destination}"
        )
        
    except Exception as e:
        db.rollback()
        return BookingResponse(
            booking_id="",
            status="error",
            message=f"Error creating booking: {str(e)}"
        )
    finally:
        if db:
            db.close()


def cancel_booking(booking_id: str, db: Session = None) -> CancellationResponse:
    """Cancel an existing booking"""
    
    if db is None:
        db = next(get_db())
    
    try:
        # Find the booking
        booking = db.query(Bookings).filter(Bookings.id == booking_id).first()
        
        if not booking:
            return CancellationResponse(
                status="error",
                message="Booking not found"
            )
        
        if booking.booking_status == "cancelled":
            return CancellationResponse(
                status="error",
                message="Booking is already cancelled"
            )
        
        # Get schedule details for response message
        schedule = db.query(TransportSchedules).filter(TransportSchedules.id == booking.schedule_id).first()
        
        # Update booking status to cancelled (soft delete)
        booking.booking_status = "cancelled"
        db.commit()
        
        message = "Booking cancelled successfully"
        if schedule:
            message = f"Booking cancelled for {schedule.transport_name} ({schedule.transport_id}) from {schedule.origin} to {schedule.destination}"
        
        return CancellationResponse(
            status="success",
            message=message
        )
        
    except Exception as e:
        db.rollback()
        return CancellationResponse(
            status="error",
            message=f"Error cancelling booking: {str(e)}"
        )
    finally:
        if db:
            db.close()


def get_user_bookings(user_id: str, db: Session = None):
    """Get all bookings for a user"""
    
    if db is None:
        db = next(get_db())
    
    try:
        bookings = db.query(Bookings).filter(
            Bookings.user_id == user_id,
            Bookings.booking_status == "confirmed"
        ).all()
        
        return bookings
        
    except Exception as e:
        print(f"Error fetching user bookings: {e}")
        return []
    finally:
        if db:
            db.close()