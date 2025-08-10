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
from sqlalchemy.orm import Session
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

        # User agent to avoid bot detection
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
        
        
        # Set page load strategy
        options.page_load_strategy = 'normal'
        
        # Prefs for blocking unnecessary content
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,
                "plugins": 2,
                "popups": 2,
                "geolocation": 2,
                "notifications": 2,
                "media_stream": 2,
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=options)
            print("Successfully initialized Edge driver using EdgeChromiumDriverManager")
            
        except Exception as e:
            print(f"EdgeChromiumDriverManager failed: {e}")
            
            edge_driver_path = os.getenv('EDGE_DRIVER_PATH')
            
            if not edge_driver_path:
                raise Exception("EDGE_DRIVER_PATH environment variable not set and EdgeChromiumDriverManager failed")
            
            try:
                service = Service(edge_driver_path)
                self.driver = webdriver.Edge(service=service, options=options)
                print(f"Successfully initialized Edge driver from local path: {edge_driver_path}")
                
            except Exception as fallback_error:
                raise Exception(f"Both EdgeChromiumDriverManager and local driver path failed. Local path error: {fallback_error}")
        
        return self.driver
    
    def search_database(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """Search for existing schedules in database first"""
        try:
            schedules = db.query(TransportSchedules).filter(
                TransportSchedules.transport_mode == query.mode,
                TransportSchedules.origin.ilike(f"%{query.origin}%"),
                TransportSchedules.destination.ilike(f"%{query.destination}%"),
                TransportSchedules.search_date == query.datetime
            ).all()
            
            if schedules:
                print(f"Found {len(schedules)} schedules in database")
                
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
                            departure_time=schedule.departure_time,
                            destination=schedule.destination,
                            arrival_time=schedule.arrival_time,
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
            else:
                print("No schedules found in database, proceeding with web scraping")
                return None
                
        except Exception as e:
            print(f"Error searching database: {e}")
            return None
    
    def save_to_database(self, schedules: List[TransportScheduleResponse], query: TravelAvailabilityQuery, db: Session):
        """Save scraped schedules to database"""
        try:
            for schedule_data in schedules:
                # Create transport schedule
                db_schedule = TransportSchedules(
                    transport_mode=schedule_data.transport_mode,
                    transport_id=schedule_data.transport_id,
                    transport_name=schedule_data.transport_name,
                    origin=schedule_data.origin,
                    departure_time=schedule_data.departure_time,
                    destination=schedule_data.destination,
                    arrival_time=schedule_data.arrival_time,
                    duration=schedule_data.duration,
                    distance=schedule_data.distance,
                    halts=schedule_data.halts,
                    origin_code=schedule_data.origin_code,
                    destination_code=schedule_data.destination_code,
                    search_date=query.datetime
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
                
                # Update schedule_data with database ID
                schedule_data.id = db_schedule.id
            
            db.commit()
            print(f"Successfully saved {len(schedules)} schedules to database")
            
        except Exception as e:
            db.rollback()
            print(f"Error saving to database: {e}")
            raise
    
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
            # Placeholder for future bus scraping
            return TravelAvailabilityResponse(
                input=query,
                schedules=[],
                status="error",
                message="Bus scraping not implemented yet",
                source="scraper"
            )
        elif query.mode == "flight":
            # Placeholder for future flight scraping
            return TravelAvailabilityResponse(
                input=query,
                schedules=[],
                status="error",
                message="Flight scraping not implemented yet",
                source="scraper"
            )
        else:
            return TravelAvailabilityResponse(
                input=query,
                schedules=[],
                status="error",
                message=f"Unsupported transport mode: {query.mode}",
                source="scraper"
            )
    
    def scrape_trains(self, query: TravelAvailabilityQuery, db: Session) -> TravelAvailabilityResponse:
        """Train-specific scraping logic"""
        
        try:
            self.setup_driver()
            
            print("Loading RailYatri website...")
            self.driver.get("https://www.railyatri.in/booking/trains-between-stations")
            
            # Wait for page to load completely
            wait = WebDriverWait(self.driver, 30)
            wait.until(EC.presence_of_element_located((By.ID, "fromstation")))
            
            print("Page loaded, waiting for interactive elements...")
            
            # Fill FROM station
            print(f"Filling FROM station: {query.origin}")
            if not self.fill_station_field("fromstation", query.origin):
                return TravelAvailabilityResponse(
                    input=query,
                    schedules=[],
                    status="error",
                    message="Failed to fill FROM station",
                    source="scraper"
                )
            
            # Fill TO station
            print(f"Filling TO station: {query.destination}")
            if not self.fill_station_field("tostation", query.destination):
                return TravelAvailabilityResponse(
                    input=query,
                    schedules=[],
                    status="error",
                    message="Failed to fill TO station",
                    source="scraper"
                )
            
            # Select date
            print(f"Selecting date: {query.datetime}")
            all_dates = self.driver.find_elements(By.CSS_SELECTOR, "[id^='date_strip_']")
            date_selected = False
            
            for date_elem in all_dates:
                date_id = date_elem.get_attribute("id")
                if query.datetime in date_id:
                    self.safe_click_element(date_elem)
                    date_selected = True
                    print(f"Date selected: {date_id}")
                    break
            
            if not date_selected:
                print("Warning: Could not find specified date, using default")
            
            time.sleep(1)  # Brief pause before clicking search
            
            # Click search button
            print("Clicking search button...")
            if not self.click_search_button():
                print("Fallback: Pressing Enter key")
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)
            
            print("Waiting for train results...")
            time.sleep(2.5)
            
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiPaper-root"))
                )
            except TimeoutException:
                return TravelAvailabilityResponse(
                    input=query,
                    schedules=[],
                    status="error",
                    message="Train results did not load within timeout",
                    source="scraper"
                )
            
            # Extract train data
            print("Extracting train data...")
            train_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".MuiPaper-root.MuiPaper-elevation1.css-we1py8")
            
            # Filter main trains (exclude alternatives)
            filtered_train_blocks = []
            for train in train_blocks:
                try:
                    alternative_parent = train.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'css-1o5dav7')]")
                    if not alternative_parent:
                        filtered_train_blocks.append(train)
                except:
                    filtered_train_blocks.append(train)
            
            print(f"Found {len(filtered_train_blocks)} main trains")
            
            schedules = []
            # Extract data for each train
            for i, train in enumerate(filtered_train_blocks):
                try:
                    schedule_info = self.extract_train_info(train)
                    schedules.append(schedule_info)
                    print(f"Extracted data for train {i+1}: {schedule_info.transport_name}")
                    
                except Exception as e:
                    print(f"Error extracting train {i+1}: {e}")
                    continue
            
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
            
        except Exception as e:
            return TravelAvailabilityResponse(
                input=query,
                schedules=[],
                status="error",
                message=f"Main execution error: {str(e)}",
                source="scraper"
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
            print(f"Element not found: {by}={value}")
            return None
    
    def safe_click_element(self, element):
        """Safely click element using JavaScript if normal click fails"""
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)
    
    def fill_station_field(self, field_id, station_name, wait_time=1.5):
        """Fill station field and handle dropdown selection"""
        try:
            station_input = self.safe_find_element(By.ID, field_id)
            if not station_input:
                return False
                
            station_input.clear()
            station_input.send_keys(station_name)
            
            time.sleep(wait_time)  
            
            option_selector = f"{field_id}-option-0"
            
            try:
                suggestion = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.ID, option_selector))
                )
                self.safe_click_element(suggestion)
                print(f"Successfully selected {station_name} using ID: {option_selector}")
                return True
                
            except TimeoutException:
                try:
                    suggestion = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[role='option']:first-child"))
                    )
                    self.safe_click_element(suggestion)
                    print(f"Successfully selected {station_name} using role=option")
                    return True
                except TimeoutException:
                    print(f"Dropdown selection failed for {station_name}, using keyboard navigation")
                    station_input.send_keys(Keys.ENTER)
                    return True
            
        except Exception as e:
            print(f"Error filling station field {field_id}: {str(e)}")
            return False
    
    def click_search_button(self):
        """Click the Modify Search button"""
        try:
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Modify Search']"))
            )
            self.safe_click_element(search_button)
            print("Search button clicked successfully")
            return True
            
        except TimeoutException:
            try:
                search_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Modify Search')]"))
                )
                self.safe_click_element(search_button)
                print("Search button clicked using text fallback")
                return True
            except TimeoutException:
                print("Could not find search button")
                return False
        
        except Exception as e:
            print(f"Error clicking search button: {str(e)}")
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
        try:
            train_name_elem = train_element.find_element(By.TAG_NAME, "a")
            full_train_text = train_name_elem.text.strip()
            
            if full_train_text:
                parts = full_train_text.split(' ', 1)
                if len(parts) >= 2:
                    transport_id = parts[0]
                    transport_name = parts[1].strip('"')
                else:
                    transport_name = full_train_text
        except:
            pass
        
        # Extract departure info
        try:
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
        except:
            pass
        
        # Extract arrival info
        try:
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
        except:
            pass
        
        # Extract journey details
        try:
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
        except:
            pass
        
        # Extract seat availability
        try:
            seat_blocks = train_element.find_elements(By.CSS_SELECTOR, "[id^='availabilityContainer_'] > div.MuiPaper-root")
            
            for seat in seat_blocks:
                try:
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
                    
                except:
                    continue
        except:
            pass
        
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