from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database_config import get_db, init_database
from schemas import (
    TravelAvailabilityQuery, 
    BookingRequest, 
    CancellationRequest,
    TravelAvailabilityResponse,
    BookingResponse,
    CancellationResponse
)
from utils import (
    create_booking,
    cancel_booking,
    get_user_bookings,
    get_booking_details,
)
from transport_scraper import TransportScraper
import asyncio
import concurrent.futures

try:
    init_database()
    print("Database initialized successfully!")
except Exception as e:
    print(f"Database initialization failed: {e}")

app = FastAPI(title="Universal Ticketing API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Universal Ticketing API is live!",
        "version": "2.0.0",
        "supported_modes": ["train", "bus", "flight"],
        "endpoints": {
            "availability": "/api/travel/availability",
            "booking": "/api/book", 
            "cancellation": "/api/cancel"
        }
    }


@app.post("/api/travel/availability", response_model=TravelAvailabilityResponse)
async def get_travel_availability(
    request: TravelAvailabilityQuery,
    db: Session = Depends(get_db)
):
    """
    Get travel availability for different transport modes.
    """
    try:
        # Validate request
        if not request.origin or not request.destination or not request.datetime:
            raise HTTPException(
                status_code=400, 
                detail="origin, destination, and datetime are required"
            )
        
        if request.mode not in ["train", "bus", "flight"]:
            raise HTTPException(
                status_code=400,
                detail="mode must be one of: train, bus, flight"
            )
        
        scraper = TransportScraper()
        
        def run_scraper():
            return scraper.scrape_availability(request, db)
        
        # Use thread pool executor for CPU-bound task
        with concurrent.futures.ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, run_scraper)
        
        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/api/book", response_model=BookingResponse)
def book_ticket(
    request: BookingRequest,
    db: Session = Depends(get_db)
):
    """
    Book a ticket for any transport mode.
    
    Creates a booking record in the database and returns booking confirmation.
    """
    try:
        if not request.user_id or not request.schedule_id:
            raise HTTPException(
                status_code=400,
                detail="user_id and schedule_id are required"
            )
        
        result = create_booking(
            user_id=request.user_id,
            schedule_id=request.schedule_id,
            seat_preferences=request.seat_preferences,
            db=db,
        )
        
        if result.status == "error":
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing booking: {str(e)}"
        )


@app.post("/api/cancel", response_model=CancellationResponse)
def cancel_ticket(
    request: CancellationRequest,
    db: Session = Depends(get_db)
):
    """
    Cancel an existing booking.
    
    Marks the booking as cancelled in the database.
    """
    try:
        if not request.booking_id:
            raise HTTPException(
                status_code=400,
                detail="booking_id is required"
            )
        
        result = cancel_booking(booking_id=request.booking_id, db=db)
        
        if result.status == "error":
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing cancellation: {str(e)}"
        )


@app.get("/api/bookings/{user_id}")
def list_user_bookings(user_id: str, db: Session = Depends(get_db)):
    bookings = get_user_bookings(user_id=user_id, db=db)
    # Return minimal list; consumer can call details endpoint for full info
    return [
        {
            "booking_id": b.id,
            "user_id": b.user_id,
            "schedule_id": b.schedule_id,
            "booking_status": b.booking_status,
            "booking_date": b.booking_date.isoformat() if b.booking_date else None,
            "seat_preferences": b.seat_preferences,
        }
        for b in bookings
    ]


@app.get("/api/booking/{booking_id}")
def get_booking(booking_id: str, db: Session = Depends(get_db)):
    detail = get_booking_details(booking_id=booking_id, db=db)
    if not detail:
        raise HTTPException(status_code=404, detail="Booking not found")
    return detail


# Additional utility endpoints
@app.get("/api/transport-modes")
def get_supported_transport_modes():
    """Get list of supported transport modes"""
    return {
        "supported_modes": ["train", "bus", "flight"],
        "implemented": ["train"],
        "coming_soon": ["bus", "flight"]
    }


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "Universal Ticketing API",
        "version": "2.0.0",
        "database": "connected"
    }


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)