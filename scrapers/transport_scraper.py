from sqlalchemy.orm import Session
from train_scraper import TrainScraper
from datetime import timedelta
from sqlalchemy import or_, and_
from typing import List, Optional
from database_config import TransportSchedules, SeatAvailability
from schemas import (
    TravelAvailabilityQuery, 
    TravelAvailabilityResponse, 
    TransportScheduleResponse,
    SeatAvailabilityResponse,
)
import utils


class TransportScraper:
    """
    Main transport scraper class that orchestrates the scraping process.
    This class focuses only on the core business logic and delegates 
    specific responsibilities to specialized classes.
    """
    
    def __init__(self):
        self.train_scraper = TrainScraper()

    def search_schedules(self, query: TravelAvailabilityQuery, db: Session) -> Optional[TravelAvailabilityResponse]:
        """Search for existing schedules in database"""
        try:
            start_of_day, end_of_day = utils.parse_query_date(query.datetime)
            
            # Query with flexible origin/destination matching and time filtering
            schedules = db.query(TransportSchedules).filter(
                TransportSchedules.transport_mode == query.mode,
                or_(
                    TransportSchedules.origin_query.ilike(f"%{query.origin}%"),
                    TransportSchedules.origin.ilike(f"%{query.origin}%")
                ),
                or_(
                    TransportSchedules.destination_query.ilike(f"%{query.destination}%"),
                    TransportSchedules.destination.ilike(f"%{query.destination}%")
                ),
                and_(
                    TransportSchedules.departure_time >= start_of_day,
                    TransportSchedules.departure_time <= end_of_day
                )
            ).all()
            
            if schedules:
                response_schedules = self._convert_to_response_format(schedules)
                
                return TravelAvailabilityResponse(
                    input=query,
                    schedules=response_schedules,
                    status="success",
                    message=f"Found {len(schedules)} schedules from database",
                    source="database"
                )
        except Exception as e:
            print(f"Database search error: {e}")
        
        return None

    def save_schedules(self, schedules: List[TransportScheduleResponse], query: TravelAvailabilityQuery, db: Session):
        """Save scraped schedules to database"""
        for schedule_data in schedules:
            # Convert time strings to datetime objects
            departure_dt = utils.time_to_datetime(schedule_data.departure_time, query.datetime)
            arrival_dt = utils.time_to_datetime(schedule_data.arrival_time, query.datetime)
            
            # Handle arrival time on next day if it's earlier than departure
            if arrival_dt <= departure_dt:
                arrival_dt += timedelta(days=1)
            
            db_schedule = TransportSchedules(
                transport_mode=schedule_data.transport_mode,
                transport_id=schedule_data.transport_id,
                transport_name=schedule_data.transport_name,
                origin=schedule_data.origin,
                departure_time=departure_dt,
                destination=schedule_data.destination,
                arrival_time=arrival_dt,
                duration=schedule_data.duration,
                distance=schedule_data.distance,
                halts=schedule_data.halts,
                origin_code=schedule_data.origin_code,
                destination_code=schedule_data.destination_code,
                origin_query=query.origin,
                destination_query=query.destination
            )
            
            db.add(db_schedule)
            db.flush()  # Get the ID
            
            # Add seat availability
            for seat in schedule_data.seat_availability:
                db_seat = SeatAvailability(
                    schedule_id=db_schedule.id,
                    class_name=seat.class_name,
                    class_description=seat.class_description,
                    status=seat.status,
                    price=seat.price
                )
                db.add(db_seat)
            
            schedule_data.id = db_schedule.id
        
        db.commit()

    def _convert_to_response_format(self, schedules: List[TransportSchedules]) -> List[TransportScheduleResponse]:
        """Convert database models to response format"""
        response_schedules = []
        
        for schedule in schedules:
            seat_availability = [
                SeatAvailabilityResponse(
                    id=seat.id,
                    class_name=seat.class_name,
                    class_description=seat.class_description,
                    status=seat.status,
                    price=seat.price
                ) for seat in schedule.seat_availability
            ]
            
            response_schedules.append(
                TransportScheduleResponse(
                    id=schedule.id,
                    transport_mode=schedule.transport_mode,
                    transport_id=schedule.transport_id,
                    transport_name=schedule.transport_name,
                    origin=schedule.origin,
                    departure_time=schedule.departure_time.strftime('%H:%M'),
                    destination=schedule.destination,
                    arrival_time=schedule.arrival_time.strftime('%H:%M'),
                    duration=schedule.duration,
                    distance=schedule.distance,
                    halts=schedule.halts,
                    origin_code=schedule.origin_code,
                    destination_code=schedule.destination_code,
                    seat_availability=seat_availability
                )
            )
        
        return response_schedules

    def get_availability(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """
        Main method to get transport availability.
        First checks database, then scrapes if needed.
        """
        # First check database for existing data
        db_result = self.database_service.search_schedules(query, db)
        if db_result:
            return db_result
        
        # If not found in database, proceed with scraping
        return self._scrape_availability(query, db)

    def _scrape_availability(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """Delegate scraping to appropriate scraper based on transport mode"""
        
        if query.mode == "train":
            return self._scrape_trains(query, db)
        elif query.mode == "bus":
            return self._create_not_implemented_response(query, "Bus scraping not implemented yet")
        elif query.mode == "flight":
            return self._create_not_implemented_response(query, "Flight scraping not implemented yet")
        else:
            return self._create_error_response(query, f"Unsupported transport mode: {query.mode}")

    def _scrape_trains(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """Handle train scraping workflow"""
        try:
            schedules = self.train_scraper.scrape_train_schedules(
                origin=query.origin,
                destination=query.destination,
                travel_date=query.datetime
            )
            
            # Save to database if we found schedules
            if schedules:
                self.database_service.save_schedules(schedules, query, db)
            
            return TravelAvailabilityResponse(
                input=query,
                schedules=schedules,
                status="success",
                message=f"Successfully scraped {len(schedules)} trains",
                source="scraper"
            )
            
        except Exception as e:
            return self._create_error_response(query, f"Train scraping error: {str(e)}")

    def _create_not_implemented_response(self, query: TravelAvailabilityQuery, message: str) -> TravelAvailabilityResponse:
        """Create a response for not implemented transport modes"""
        return TravelAvailabilityResponse(
            input=query,
            schedules=[],
            status="error",
            message=message,
            source="scraper"
        )

    def _create_error_response(self, query: TravelAvailabilityQuery, message: str) -> TravelAvailabilityResponse:
        """Create an error response"""
        return TravelAvailabilityResponse(
            input=query,
            schedules=[],
            status="error",
            message=message,
            source="scraper"
        )