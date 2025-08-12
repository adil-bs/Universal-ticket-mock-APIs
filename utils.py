from sqlalchemy.orm import Session
from database_config import Bookings, TransportSchedules, SeatAvailability, get_db
from schemas import BookingResponse, CancellationResponse, SeatPreferences, BookingDetail, TransportScheduleResponse, SeatAvailabilityResponse
import uuid
import re


def decide_train_booking_outcome(status_text: str) -> str:
    """Map scraped seat availability status to booking outcome for trains.

    Returns either: 'confirmed', 'waitlist', 'regret'
    """
    if not status_text:
        return "regret"

    text = status_text.strip().lower()

    # Direct availability like "3 Available" or "Available"
    if "available" in text:
        # Any non-zero available is confirmed
        number_match = re.search(r"(\d+)\s*available", text)
        if number_match:
            try:
                if int(number_match.group(1)) > 0:
                    return "confirmed"
            except ValueError:
                pass
        # If says available but can't parse number, assume confirmed
        return "confirmed"

    # Regret means not available
    if "regret" in text:
        return "regret"

    # Waitlist cases
    if "waitlist" in text or "wl" in text:
        return "waitlist"

    # Fallback
    return "regret"


def create_booking(
    user_id: str,
    schedule_id: int,
    db: Session = None,
    seat_preferences: SeatPreferences | None = None,
) -> BookingResponse:
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

        # Validate seat preferences
        if seat_preferences is None or not seat_preferences.seat_class:
            return BookingResponse(
                booking_id="",
                status="error",
                message="seat_preferences.seat_class is required"
            )

        # Check seat availability for the requested seat_class on this schedule
        seat_status_row = (
            db.query(SeatAvailability)
            .filter(
                SeatAvailability.schedule_id == schedule_id,
                SeatAvailability.class_name.ilike(seat_preferences.seat_class)
            )
            .first()
        )

        if not seat_status_row:
            return BookingResponse(
                booking_id="",
                status="error",
                message=f"No seat availability data for class '{seat_preferences.seat_class}'"
            )

        outcome = decide_train_booking_outcome(seat_status_row.status)
        
        # Create new booking with collision-safe id generation
        booking_id = str(uuid.uuid4())

        
        new_booking = Bookings(
            id=booking_id,
            user_id=user_id,
            schedule_id=schedule_id,
            booking_status=outcome,
            seat_preferences=seat_preferences.dict()
        )
        
        db.add(new_booking)
        db.commit()
        
        return BookingResponse(
            booking_id=booking_id,
            status="success",
            message=(
                f"Booking {outcome} for {schedule.transport_name} ({schedule.transport_id}) "
                f"from {schedule.origin} to {schedule.destination} in {seat_preferences.seat_class}"
            ),
            booking_status=outcome,
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
        bookings = db.query(Bookings).filter(Bookings.user_id == user_id).all()
        return bookings
        
    except Exception as e:
        print(f"Error fetching user bookings: {e}")
        return []
    finally:
        if db:
            db.close()


def get_booking_details(booking_id: str, db: Session = None) -> BookingDetail | None:
    if db is None:
        db = next(get_db())
    try:
        booking = db.query(Bookings).filter(Bookings.id == booking_id).first()
        if not booking:
            return None
        schedule = db.query(TransportSchedules).filter(TransportSchedules.id == booking.schedule_id).first()
        schedule_resp = TransportScheduleResponse(
            id=schedule.id,
            transport_mode=schedule.transport_mode,
            transport_id=schedule.transport_id,
            transport_name=schedule.transport_name,
            origin=schedule.origin,
            departure_time=schedule.departure_time.isoformat() if schedule.departure_time else "",
            destination=schedule.destination,
            arrival_time=schedule.arrival_time.isoformat() if schedule.arrival_time else "",
            duration=schedule.duration,
            distance=schedule.distance,
            halts=schedule.halts,
            origin_code=schedule.origin_code or "",
            destination_code=schedule.destination_code or "",
        ) if schedule else None
        
        return BookingDetail(
            booking_id=booking.id,
            user_id=booking.user_id,
            schedule_id=booking.schedule_id,
            booking_status=booking.booking_status,
            booking_date=booking.booking_date.isoformat() if booking.booking_date else None,
            seat_preferences=booking.seat_preferences,
            schedule=schedule_resp,
        )
    finally:
        if db:
            db.close()