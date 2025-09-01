from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import List
import time
import re

from scrapers.webdriver_manager import WebDriverManager
from schemas import TransportScheduleResponse, SeatAvailabilityResponse
import scrapers.utils as utils


class FlightScraper(WebDriverManager):
    """Handles flight-specific scraping operations"""

    def scrape_flight_schedules(self, origin: str, destination: str, travel_date: str) -> List[TransportScheduleResponse]:
        """Scrape flight schedules from ixigo.com"""
        
        self.setup_driver()
        
        try:
            self.driver.get("https://www.ixigo.com/flights")
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='originId']"))
            )
            
            # Fill origin and destination
            if not self._fill_location_field("origin", origin):
                raise Exception("Failed to fill FROM location")
            
            if not self._fill_location_field("destination", destination):
                raise Exception("Failed to fill TO location")
            
            # Select date
            self._select_travel_date(travel_date)
            
            # Search
            self._perform_search()
            
            # Wait for results and extract data
            self._wait_for_flight_results()
            
            return self._extract_flight_schedules()
            
        finally:
            self.quit()

    def _fill_location_field(self, field_type: str, location: str) -> bool:
        """Fill location field (origin/destination) and handle dropdown selection"""
        try:
            # Click on the appropriate field
            if field_type == "origin":
                field_selector = "[data-testid='originId']"
            else:
                field_selector = "[data-testid='destinationId']"
            
            print("before location field")
            location_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, field_selector))
            )
            print("after location field")
            self.safe_click_element(location_field)
            time.sleep(1)
            print("after click location field")
            # Find the input field that becomes visible
            input_field = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[value='']"))
            )
            print("after location field")
            # Clear and type location
            input_field.clear()
            print("after clear location")
            input_field.send_keys(location)
            time.sleep(2)
            print("after send keys")
            # Select first option from dropdown
            try:
                first_option = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".list-sm .bf"))
                )
                self.safe_click_element(first_option)
                return True
            except TimeoutException:
                # Fallback: press enter
                input_field.send_keys(Keys.ENTER)
                return True
                
        except Exception as e:
            print(f"Error filling {field_type} field: {e}")
            return False

    def _select_travel_date(self, travel_date: str):
        """Select travel date from calendar picker"""
        try:
            # Click on departure date field
            departure_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='departureDate']"))
            )
            self.safe_click_element(departure_field)
            time.sleep(1)
            
            # Extract day and month from travel_date
            day, month_name = utils.extract_day_month_from_date(travel_date)
            
            # Find and click the appropriate date in calendar
            self._click_calendar_date(day)
            
        except Exception as e:
            print(f"Error selecting travel date: {e}")
            # Continue with default date if selection fails

    def _click_calendar_date(self, target_day: str):
        """Click on the specific date in the calendar"""
        try:
            # Look for the date button with the target day
            date_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, 
                ".react-calendar__month-view__days__day:not([disabled])"
            )
            
            for button in date_buttons:
                abbr_elem = button.find_element(By.TAG_NAME, "abbr")
                if abbr_elem.text.strip() == target_day:
                    self.safe_click_element(button)
                    return True
            
            print(f"Could not find date {target_day} in calendar")
            return False
            
        except Exception as e:
            print(f"Error clicking calendar date: {e}")
            return False

    def _perform_search(self):
        """Click search button to initiate flight search"""
        try:
            # Look for search button by text content
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Search')]"))
            )
            self.safe_click_element(search_button)
            time.sleep(2)
        except TimeoutException:
            # Fallback: look for search button by class or other attributes
            try:
                search_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for button in search_buttons:
                    if "search" in button.text.lower():
                        self.safe_click_element(button)
                        time.sleep(2)
                        break
                else:
                    print("Could not find search button")
            except Exception as e:
                print(f"Could not find search button: {e}")

    def _wait_for_flight_results(self):
        """Wait for flight results to load"""
        try:
            # Wait for the listing container to appear
            WebDriverWait(self.driver, 45).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".listingContainer"))
            )
            
            # Additional wait for flight cards to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".shadow-card.bg-white.rounded-10"))
            )
            
            # Wait a bit more for all flights to load
            time.sleep(5)
            
        except TimeoutException:
            print("Timeout waiting for flight results")

    def _extract_flight_schedules(self) -> List[TransportScheduleResponse]:
        """Extract flight schedules from the results page"""
        flight_cards = self.driver.find_elements(
            By.CSS_SELECTOR, 
            ".shadow-card.bg-white.rounded-10.cursor-pointer"
        )
        
        schedules = []
        for card in flight_cards[:20]:  # Limit to first 20 flights for performance
            schedule_info = self._extract_single_flight_info(card)
            if schedule_info:
                schedules.append(schedule_info)
        
        return schedules

    def _extract_single_flight_info(self, flight_card) -> TransportScheduleResponse:
        """Extract information from a single flight card"""
        
        # Initialize variables
        transport_id = ""
        transport_name = ""
        origin = ""
        departure_time = ""
        destination = ""
        arrival_time = ""
        duration = ""
        origin_code = ""
        destination_code = ""
        
        try:
            # Extract airline info
            airline_info = self._extract_airline_info(flight_card)
            transport_name = airline_info.get('name', '')
            transport_id = airline_info.get('code', '')
            
            # Extract timing info
            timing_info = self._extract_timing_info(flight_card)
            departure_time = timing_info.get('departure_time', '')
            arrival_time = timing_info.get('arrival_time', '')
            origin_code = timing_info.get('origin_code', '')
            destination_code = timing_info.get('destination_code', '')
            duration = timing_info.get('duration', '')
            
            # Extract location names (fallback from codes)
            origin = origin_code
            destination = destination_code
            
            # Extract seat availability (fare types)
            seat_availability = self._extract_seat_availability(flight_card)
            
            return TransportScheduleResponse(
                transport_mode="flight",
                transport_id=transport_id,
                transport_name=transport_name,
                origin=origin,
                departure_time=departure_time,
                destination=destination,
                arrival_time=arrival_time,
                duration=duration,
                distance="",  # Not typically shown for flights
                halts=self._extract_stops_info(flight_card),
                origin_code=origin_code,
                destination_code=destination_code,
                seat_availability=seat_availability
            )
            
        except Exception as e:
            print(f"Error extracting flight info: {e}")
            return None

    def _extract_airline_info(self, flight_card) -> dict:
        """Extract airline name and flight code"""
        try:
            # Get airline name
            airline_name_elem = flight_card.find_element(By.CSS_SELECTOR, ".airlineTruncate")
            airline_name = airline_name_elem.text.strip()
            
            # Get flight code
            flight_code_elem = flight_card.find_element(By.CSS_SELECTOR, ".pc_maxW115__wjiZg")
            flight_code = flight_code_elem.text.strip()
            
            return {
                'name': airline_name,
                'code': flight_code
            }
        except Exception as e:
            print(f"Error extracting airline info: {e}")
            return {'name': '', 'code': ''}

    def _extract_timing_info(self, flight_card) -> dict:
        """Extract departure/arrival times and airport codes"""
        try:
            # Extract departure info
            dep_time_elem = flight_card.find_element(By.CSS_SELECTOR, ".timeTileList .h6")
            departure_time = dep_time_elem.text.strip()
            
            dep_code_elem = flight_card.find_element(By.CSS_SELECTOR, ".timeTileList .body-sm")
            origin_code = dep_code_elem.text.strip()
            
            # Extract arrival info (second timeTileList)
            time_tiles = flight_card.find_elements(By.CSS_SELECTOR, ".timeTileList")
            if len(time_tiles) >= 2:
                arr_time_elem = time_tiles[1].find_element(By.CSS_SELECTOR, ".h6")
                arrival_time = arr_time_elem.text.strip()
                
                arr_code_elem = time_tiles[1].find_element(By.CSS_SELECTOR, ".body-sm")
                destination_code = arr_code_elem.text.strip()
            else:
                arrival_time = ""
                destination_code = ""
            
            # Extract duration
            duration_elem = flight_card.find_element(By.CSS_SELECTOR, ".text-center .body-sm")
            duration = duration_elem.text.strip()
            
            return {
                'departure_time': departure_time,
                'arrival_time': arrival_time,
                'origin_code': origin_code,
                'destination_code': destination_code,
                'duration': duration
            }
        except Exception as e:
            print(f"Error extracting timing info: {e}")
            return {
                'departure_time': '', 'arrival_time': '',
                'origin_code': '', 'destination_code': '', 'duration': ''
            }

    def _extract_stops_info(self, flight_card) -> str:
        """Extract stops/layover information"""
        try:
            stops_elem = flight_card.find_element(By.CSS_SELECTOR, ".text-center .body-sm:last-child")
            stops_text = stops_elem.text.strip()
            return stops_text
        except Exception:
            return "Non-stop"

    def _extract_seat_availability(self, flight_card) -> List[SeatAvailabilityResponse]:
        """Extract fare types and prices as seat availability"""
        seat_availability = []
        
        try:
            # First try to get the main price displayed
            try:
                price_elem = flight_card.find_element(By.CSS_SELECTOR, "[data-testid='pricing']")
                main_price = utils.clean_price_text(price_elem.text)
                
                # Add as Economy class (default)
                seat_availability.append(
                    SeatAvailabilityResponse(
                        class_name="Economy",
                        class_description="Regular Fare",
                        status="Available",
                        price=main_price
                    )
                )
            except Exception as e:
                print(f"Error extracting main price: {e}")
            
            # Try to expand fare options by clicking "View Fares" button
            try:
                view_fares_buttons = flight_card.find_elements(
                    By.XPATH, 
                    ".//button[contains(text(), 'View Fares')]"
                )
                if view_fares_buttons:
                    self.safe_click_element(view_fares_buttons[0])
                    time.sleep(2)
                    
                    # Now try to extract different fare types
                    fare_sections = flight_card.find_elements(By.CSS_SELECTOR, ".border.p-15.rounded-10")
                    for fare_section in fare_sections:
                        try:
                            # Extract fare type name
                            fare_name_elems = fare_section.find_elements(By.CSS_SELECTOR, ".body-sm.font-medium")
                            if fare_name_elems:
                                fare_name = fare_name_elems[0].text.strip()
                            else:
                                fare_name = "Standard"
                            
                            # Extract price from this fare section
                            price_elems = fare_section.find_elements(By.CSS_SELECTOR, "[data-testid='pricing']")
                            if price_elems:
                                fare_price = utils.clean_price_text(price_elems[0].text)
                            else:
                                # Try alternative price selectors
                                price_texts = fare_section.find_elements(By.CSS_SELECTOR, ".h5, .h6")
                                for price_elem in price_texts:
                                    if "₹" in price_elem.text:
                                        fare_price = utils.clean_price_text(price_elem.text)
                                        break
                                else:
                                    fare_price = "N/A"
                            
                            # Only add if it's different from already added fares
                            if not any(seat.class_name == fare_name for seat in seat_availability):
                                seat_availability.append(
                                    SeatAvailabilityResponse(
                                        class_name=fare_name,
                                        class_description=fare_name,
                                        status="Available",
                                        price=fare_price
                                    )
                                )
                        except Exception as e:
                            print(f"Error extracting individual fare: {e}")
                            continue
            except Exception as e:
                print(f"Error expanding fare options: {e}")
                
        except Exception as e:
            print(f"Error extracting seat availability: {e}")
        
        # If no seat availability found, add a default entry
        if not seat_availability:
            seat_availability.append(
                SeatAvailabilityResponse(
                    class_name="Economy",
                    class_description="Standard",
                    status="Available", 
                    price="N/A"
                )
            )
        
        return seat_availability