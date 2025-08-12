from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# Travel Availability Query
class TravelAvailabilityQuery(BaseModel):
    mode: str  # train, bus, flight
    origin: str
    destination: str
    datetime: str

class SeatPreferences(BaseModel):
    seat_class: str
    seat_position: Optional[str] = None  # window, aisle, upper, lower, etc
    coach: Optional[str] = None
    seat_number: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

class BookingRequest(BaseModel):
    user_id: str
    schedule_id: int
    seat_preferences: SeatPreferences

class CancellationRequest(BaseModel):
    booking_id: str

class BookingResponse(BaseModel):
    booking_id: str
    status: str
    message: str
    booking_status: Optional[str] = None  # confirmed, waitlist, regret


class BookingDetail(BaseModel):
    booking_id: str
    user_id: str
    schedule_id: int
    booking_status: str
    booking_date: Optional[str] = None
    seat_preferences: Optional[Dict[str, Any]] = None
    schedule: Optional["TransportScheduleResponse"] = None


class CancellationResponse(BaseModel):
    status: str
    message: str


# Seat Availability Schema
class SeatAvailabilityResponse(BaseModel):
    id: Optional[int] = None
    class_name: str = ""
    class_description: str = ""
    status: str = ""
    price: str = ""


class TransportScheduleResponse(BaseModel):
    id: Optional[int] = None
    transport_mode: str = "train"
    transport_id: str = ""
    transport_name: str = ""
    origin: str = ""
    departure_time: str = ""
    destination: str = ""
    arrival_time: str = ""
    duration: str = ""
    distance: Optional[str] = None  # Can be str or None
    halts: Optional[str] = None 
    origin_code: str = ""
    destination_code: str = ""
    seat_availability: List[SeatAvailabilityResponse] = []


class TravelAvailabilityResponse(BaseModel):
    input: TravelAvailabilityQuery
    schedules: List[TransportScheduleResponse] = []
    status: str = "success"
    message: Optional[str] = None
    source: str = "database"  # database or scraped