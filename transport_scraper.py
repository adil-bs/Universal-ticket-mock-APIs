from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from typing import List
import time
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from database_config import TransportSchedules, SeatAvailability, get_db
from schemas import (
    TravelAvailabilityQuery, 
    TravelAvailabilityResponse, 
    TransportScheduleResponse,
    SeatAvailabilityResponse,
)


class TransportScraper:
    """Unified scraper class for different transport modes"""
    
    def __init__(self):
        self.driver = None

    @staticmethod
    def datetime_to_ddmm(datetime_str: str) -> str:
        """
        Convert datetime string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS) to DDMM format
        Examples: "2024-08-11" -> "11Aug", "2024-05-01" -> "1May"
        """
        try:
            # Handle both with and without time part
            if ' ' in datetime_str:
                date_part = datetime_str.split(' ')[0]
            else:
                date_part = datetime_str
            
            dt = datetime.strptime(date_part, '%Y-%m-%d')
            
            # Get day without leading zero
            day = str(dt.day)
            
            # Get month abbreviation
            month_names = {
                1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
            }
            month = month_names[dt.month]
            
            return f"{day}{month}"
        except Exception as e:
            print(f"Error converting datetime {datetime_str} to DDMM format: {e}")
            return datetime_str

    @staticmethod
    def time_to_datetime(time_str: str, base_date: str) -> datetime:
        """
        Convert time string (HH:MM) to full datetime using base_date
        Args:
            time_str: Time in format "HH:MM"
            base_date: Date string in format "YYYY-MM-DD"
        Returns:
            datetime object
        """
        try:
            # Handle base_date with or without time part
            if ' ' in base_date:
                date_part = base_date.split(' ')[0]
            else:
                date_part = base_date
            
            # Combine date and time
            datetime_str = f"{date_part} {time_str}:00"
            return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"Error converting time {time_str} with base date {base_date}: {e}")
            # Return a default datetime if conversion fails
            return datetime.strptime(f"{base_date} 00:00:00", '%Y-%m-%d %H:%M:%S')

    def setup_driver(self):
        """Setup Edge WebDriver with EdgeChromiumDriverManager and fallback"""
        options = Options()
        
        # Basic options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--mute-audio")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
        options.page_load_strategy = 'normal'
        
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2, "plugins": 2, "popups": 2,
                "geolocation": 2, "notifications": 2, "media_stream": 2,
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=options)
        except Exception as e:
            edge_driver_path = os.getenv('EDGE_DRIVER_PATH')
            if not edge_driver_path:
                raise Exception("EDGE_DRIVER_PATH environment variable not set and EdgeChromiumDriverManager failed")
            
            service = Service(edge_driver_path)
            self.driver = webdriver.Edge(service=service, options=options)
        
        return self.driver
    
    def search_database(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """Search for existing schedules in database first"""
        try:
            # Parse the query datetime to get start and end of day
            if ' ' in query.datetime:
                date_part = query.datetime.split(' ')[0]
            else:
                date_part = query.datetime
            
            query_date = datetime.strptime(date_part, '%Y-%m-%d')
            start_of_day = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = query_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
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
    
    def save_to_database(self, schedules: List[TransportScheduleResponse], query: TravelAvailabilityQuery, db: Session):
        """Save scraped schedules to database"""
        for schedule_data in schedules:
            # Convert time strings to datetime objects
            departure_dt = self.time_to_datetime(schedule_data.departure_time, query.datetime)
            arrival_dt = self.time_to_datetime(schedule_data.arrival_time, query.datetime)
            
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
    
    def scrape_availability(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """Main method to get availability - check database first, then scrape if needed"""
        
        # First check database
        db_result = self.search_database(query, db)
        if db_result:
            return db_result
        
        # If not found in database, proceed with scraping
        if query.mode == "train":
            return self.scrape_trains(query, db)
        elif query.mode == "bus":
            return TravelAvailabilityResponse(
                input=query, schedules=[], status="error",
                message="Bus scraping not implemented yet", source="scraper"
            )
        elif query.mode == "flight":
            return TravelAvailabilityResponse(
                input=query, schedules=[], status="error",
                message="Flight scraping not implemented yet", source="scraper"
            )
        else:
            return TravelAvailabilityResponse(
                input=query, schedules=[], status="error",
                message=f"Unsupported transport mode: {query.mode}", source="scraper"
            )
    
    def scrape_trains(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """Train-specific scraping logic"""
        
        try:
            self.setup_driver()
            self.driver.get("https://www.railyatri.in/booking/trains-between-stations")
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, "fromstation"))
            )
            
            # Fill stations
            if not self.fill_station_field("fromstation", query.origin):
                return TravelAvailabilityResponse(
                    input=query, schedules=[], status="error",
                    message="Failed to fill FROM station", source="scraper"
                )
            
            if not self.fill_station_field("tostation", query.destination):
                return TravelAvailabilityResponse(
                    input=query, schedules=[], status="error",
                    message="Failed to fill TO station", source="scraper"
                )
            
            # Select date using converted DDMM format
            ddmm_date = self.datetime_to_ddmm(query.datetime)
            all_dates = self.driver.find_elements(By.CSS_SELECTOR, "[id^='date_strip_']")
            date_selected = False
            
            for date_elem in all_dates:
                date_id = date_elem.get_attribute("id")
                if ddmm_date in date_id:
                    self.safe_click_element(date_elem)
                    date_selected = True
                    break
            
            if not date_selected:
                print("Warning: Could not find specified date, using default")
            
            time.sleep(1)
            
            # Click search button
            if not self.click_search_button():
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)
            
            time.sleep(2.5)
            
            # Wait for results
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiPaper-root"))
            )
            
            # Extract train data
            train_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".MuiPaper-root.MuiPaper-elevation1.css-we1py8")
            
            # Filter main trains (exclude alternatives)
            filtered_train_blocks = []
            for train in train_blocks:
                alternative_parent = train.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'css-1o5dav7')]")
                if not alternative_parent:
                    filtered_train_blocks.append(train)
            
            schedules = []
            for train in filtered_train_blocks:
                schedule_info = self.extract_train_info(train)
                if schedule_info:
                    schedules.append(schedule_info)
            
            # Save to database
            if schedules:
                self.save_to_database(schedules, query, db)
            
            return TravelAvailabilityResponse(
                input=query,
                schedules=schedules,
                status="success",
                message=f"Successfully scraped {len(schedules)} trains",
                source="scraper"
            )
            
        except TimeoutException:
            return TravelAvailabilityResponse(
                input=query, schedules=[], status="error",
                message="Train results did not load within timeout", source="scraper"
            )
        except Exception as e:
            return TravelAvailabilityResponse(
                input=query, schedules=[], status="error",
                message=f"Scraping error: {str(e)}", source="scraper"
            )
        finally:
            if self.driver:
                self.driver.quit()
    
    def safe_find_element(self, by, value, timeout=10):
        """Safely find element with timeout"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
    
    def safe_click_element(self, element):
        """Safely click element using JavaScript if normal click fails"""
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)
    
    def fill_station_field(self, field_id, station_name, wait_time=1.5):
        """Fill station field and handle dropdown selection"""
        station_input = self.safe_find_element(By.ID, field_id)
        if not station_input:
            return False
            
        station_input.clear()
        station_input.send_keys(station_name)
        time.sleep(wait_time)
        
        # Try different selection methods
        option_selector = f"{field_id}-option-0"
        
        try:
            suggestion = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, option_selector))
            )
            self.safe_click_element(suggestion)
            return True
        except TimeoutException:
            try:
                suggestion = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[role='option']:first-child"))
                )
                self.safe_click_element(suggestion)
                return True
            except TimeoutException:
                station_input.send_keys(Keys.ENTER)
                return True
    
    def click_search_button(self):
        """Click the Modify Search button"""
        try:
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Modify Search']"))
            )
            self.safe_click_element(search_button)
            return True
        except TimeoutException:
            try:
                search_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Modify Search')]"))
                )
                self.safe_click_element(search_button)
                return True
            except TimeoutException:
                return False
    
    def extract_train_info(self, train_element) -> TransportScheduleResponse:
        """Extract information from a single train element"""
        
        transport_id = ""
        transport_name = ""
        origin = ""
        departure_time = ""
        destination = ""
        arrival_time = ""
        duration = ""
        distance = ""
        halts = ""
        origin_code = ""
        destination_code = ""
        seat_availability = []
        
        # Extract train name and number
        train_name_elem = train_element.find_element(By.TAG_NAME, "a")
        full_train_text = train_name_elem.text.strip()
        
        if full_train_text:
            parts = full_train_text.split(' ', 1)
            if len(parts) >= 2:
                transport_id = parts[0]
                transport_name = parts[1].strip('"')
            else:
                transport_name = full_train_text
        
        # Extract departure info
        dep_elem = train_element.find_element(By.CSS_SELECTOR, ".css-i9gxme p")
        dep_text = dep_elem.text.strip()
        dep_lines = dep_text.split('\n')
        if len(dep_lines) >= 2:
            time_part = dep_lines[0].strip()
            if ',' in time_part:
                code_time = time_part.split(',')
                if len(code_time) >= 2:
                    origin_code = code_time[0].strip()
                    departure_time = code_time[1].strip()
            origin = dep_lines[1].strip()
        
        # Extract arrival info
        arr_elem = train_element.find_element(By.CSS_SELECTOR, ".css-13tuif5 p")
        arr_text = arr_elem.text.strip()
        arr_lines = arr_text.split('\n')
        if len(arr_lines) >= 2:
            time_part = arr_lines[0].strip()
            if ',' in time_part:
                time_code = time_part.split(',')
                if len(time_code) >= 2:
                    arrival_time = time_code[0].strip()
                    destination_code = time_code[1].strip()
            destination = arr_lines[1].strip()
        
        # Extract journey details
        duration_elem = train_element.find_element(By.CSS_SELECTOR, ".css-0 > span:nth-child(1)")
        mins_elem = train_element.find_element(By.CSS_SELECTOR, ".css-0 > span:nth-child(2)")
        duration = f"{duration_elem.text} {mins_elem.text}"
        
        journey_info = train_element.find_element(By.CSS_SELECTOR, ".css-1305zog:nth-child(2)")
        journey_text = journey_info.text.strip()
        if '|' in journey_text:
            parts = journey_text.split('|')
            if len(parts) >= 2:
                halts = parts[0].strip()
                distance = parts[1].strip()
        
        # Extract seat availability
        seat_blocks = train_element.find_elements(By.CSS_SELECTOR, "[id^='availabilityContainer_'] > div.MuiPaper-root")
        
        for seat in seat_blocks:
            if "taptorefresh" in seat.get_attribute("innerHTML").lower():
                continue
            
            class_name = ""
            class_description = ""
            status = ""
            price = ""
            
            # Extract seat class
            seat_class_elem = seat.find_element(By.CSS_SELECTOR, ".bookingclasstitle")
            class_text = seat_class_elem.text.strip()
            
            if '(' in class_text and ')' in class_text:
                class_parts = class_text.split('(')
                class_name = class_parts[0].strip()
                if len(class_parts) > 1:
                    class_description = class_parts[1].replace(')', '').strip()
            else:
                class_name = class_text
            
            # Extract availability status
            seat_status_elem = seat.find_element(By.CSS_SELECTOR, ".availibilityandseatcounttitle")
            status = seat_status_elem.text.strip()
            
            # Extract price
            try:
                price_elem = seat.find_element(By.CSS_SELECTOR, ".bookingclassprice")
                price_text = price_elem.text.strip()
                price = price_text.replace('₹', '').strip()
            except:
                price = "N/A"
            
            seat_availability.append(
                SeatAvailabilityResponse(
                    class_name=class_name,
                    class_description=class_description,
                    status=status,
                    price=price
                )
            )
        
        return TransportScheduleResponse(
            transport_mode="train",
            transport_id=transport_id,
            transport_name=transport_name,
            origin=origin,
            departure_time=departure_time,
            destination=destination,
            arrival_time=arrival_time,
            duration=duration,
            distance=distance,
            halts=halts,
            origin_code=origin_code,
            destination_code=destination_code,
            seat_availability=seat_availability
        )