from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# Travel Availability Query
class TravelAvailabilityQuery(BaseModel):
    mode: str  # train, bus, flight
    origin: str
    destination: str
    datetime: str

class BookingRequest(BaseModel):
    user_id: str
    schedule_id: int
    # seat_class: Optional[str] = None

class CancellationRequest(BaseModel):
    booking_id: str

class BookingResponse(BaseModel):
    booking_id: str
    status: str
    message: str


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