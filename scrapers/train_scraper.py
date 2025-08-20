from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from typing import List
import time

from scrapers.webdriver_manager import WebDriverManager
from schemas import TransportScheduleResponse, SeatAvailabilityResponse
import scrapers.utils as utils


class TrainScraper(WebDriverManager):
    """Handles train-specific scraping operations"""

    def scrape_train_schedules(self, origin: str, destination: str, travel_date: str) -> List[TransportScheduleResponse]:
        """Scrape train schedules from railyatri.in"""
        
        self.setup_driver()
        
        try:
            self.driver.get("https://www.railyatri.in/booking/trains-between-stations")
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, "fromstation"))
            )
            
            # Fill stations
            if not self._fill_station_field("fromstation", origin):
                raise Exception("Failed to fill FROM station")
            
            if not self._fill_station_field("tostation", destination):
                raise Exception("Failed to fill TO station")
            
            # Select date
            self._select_travel_date(travel_date)
            
            # Search
            self._perform_search()
            
            # Wait for results and extract data
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiPaper-root"))
            )
            
            return self._extract_train_schedules()
            
        finally:
            self.quit()

    def _fill_station_field(self, field_id: str, station_name: str, wait_time: float = 1.5) -> bool:
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

    def _select_travel_date(self, travel_date: str):
        """Select travel date from date picker"""
        ddmm_date = utils.datetime_to_ddmm(travel_date)
        all_dates = self.driver.find_elements(By.CSS_SELECTOR, "[id^='date_strip_']")
        
        for date_elem in all_dates:
            date_id = date_elem.get_attribute("id")
            if ddmm_date in date_id:
                self.safe_click_element(date_elem)
                return
        
        print("Warning: Could not find specified date, using default")

    def _perform_search(self):
        """Click search button and initiate search"""
        time.sleep(1)
        
        if not self._click_search_button():
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)
        
        time.sleep(2.5)

    def _click_search_button(self) -> bool:
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

    def _extract_train_schedules(self) -> List[TransportScheduleResponse]:
        """Extract train schedules from the results page"""
        train_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".MuiPaper-root.MuiPaper-elevation1.css-we1py8")
        
        # Filter main trains (exclude alternatives)
        filtered_train_blocks = []
        for train in train_blocks:
            alternative_parent = train.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'css-1o5dav7')]")
            if not alternative_parent:
                filtered_train_blocks.append(train)
        
        schedules = []
        for train in filtered_train_blocks:
            schedule_info = self._extract_single_train_info(train)
            if schedule_info:
                schedules.append(schedule_info)
        
        return schedules

    def _extract_single_train_info(self, train_element) -> TransportScheduleResponse:
        """Extract information from a single train element"""
        
        # Initialize variables
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
        departure_time, origin, origin_code = self._extract_departure_info(train_element)
        
        # Extract arrival info
        arrival_time, destination, destination_code = self._extract_arrival_info(train_element)
        
        # Extract journey details
        duration = self._extract_duration(train_element)
        halts, distance = self._extract_journey_details(train_element)
        
        # Extract seat availability
        seat_availability = self._extract_seat_availability(train_element)
        
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

    def _extract_departure_info(self, train_element) -> tuple[str, str, str]:
        """Extract departure time, origin, and origin code"""
        dep_elem = train_element.find_element(By.CSS_SELECTOR, ".css-i9gxme p")
        dep_text = dep_elem.text.strip()
        dep_lines = dep_text.split('\n')
        
        departure_time = ""
        origin = ""
        origin_code = ""
        
        if len(dep_lines) >= 2:
            time_part = dep_lines[0].strip()
            if ',' in time_part:
                code_time = time_part.split(',')
                if len(code_time) >= 2:
                    origin_code = code_time[0].strip()
                    departure_time = code_time[1].strip()
            origin = dep_lines[1].strip()
        
        return departure_time, origin, origin_code

    def _extract_arrival_info(self, train_element) -> tuple[str, str, str]:
        """Extract arrival time, destination, and destination code"""
        arr_elem = train_element.find_element(By.CSS_SELECTOR, ".css-13tuif5 p")
        arr_text = arr_elem.text.strip()
        arr_lines = arr_text.split('\n')
        
        arrival_time = ""
        destination = ""
        destination_code = ""
        
        if len(arr_lines) >= 2:
            time_part = arr_lines[0].strip()
            if ',' in time_part:
                time_code = time_part.split(',')
                if len(time_code) >= 2:
                    arrival_time = time_code[0].strip()
                    destination_code = time_code[1].strip()
            destination = arr_lines[1].strip()
        
        return arrival_time, destination, destination_code

    def _extract_duration(self, train_element) -> str:
        """Extract journey duration"""
        duration_elem = train_element.find_element(By.CSS_SELECTOR, ".css-0 > span:nth-child(1)")
        mins_elem = train_element.find_element(By.CSS_SELECTOR, ".css-0 > span:nth-child(2)")
        return f"{duration_elem.text} {mins_elem.text}"

    def _extract_journey_details(self, train_element) -> tuple[str, str]:
        """Extract halts and distance information"""
        try:
            journey_info = train_element.find_element(By.CSS_SELECTOR, ".css-1305zog:nth-child(2)")
            journey_text = journey_info.text.strip()
            if '|' in journey_text:
                parts = journey_text.split('|')
                if len(parts) >= 2:
                    return parts[0].strip(), parts[1].strip()
        except Exception:
            pass
        
        return "", ""

    def _extract_seat_availability(self, train_element) -> List[SeatAvailabilityResponse]:
        """Extract seat availability information"""
        seat_availability = []
        seat_blocks = train_element.find_elements(By.CSS_SELECTOR, "[id^='availabilityContainer_'] > div.MuiPaper-root")

        for seat in seat_blocks:
            if "taptorefresh" in seat.get_attribute("innerHTML").lower():
                continue
            
            class_name, class_description = self._extract_seat_class(seat)
            status = self._extract_seat_status(seat)
            price = self._extract_seat_price(seat)
            
            seat_availability.append(
                SeatAvailabilityResponse(
                    class_name=class_name,
                    class_description=class_description,
                    status=status,
                    price=price
                )
            )
        
        return seat_availability

    def _extract_seat_class(self, seat_element) -> tuple[str, str]:
        """Extract seat class name and description"""
        seat_class_elem = seat_element.find_element(By.CSS_SELECTOR, ".bookingclasstitle")
        class_text = seat_class_elem.text.strip()
        
        class_name = ""
        class_description = ""
        
        if '(' in class_text and ')' in class_text:
            class_parts = class_text.split('(')
            class_name = class_parts[0].strip()
            if len(class_parts) > 1:
                class_description = class_parts[1].replace(')', '').strip()
        else:
            class_name = class_text
        
        return class_name, class_description

    def _extract_seat_status(self, seat_element) -> str:
        """Extract seat availability status"""
        seat_status_elem = seat_element.find_element(By.CSS_SELECTOR, ".availibilityandseatcounttitle")
        return seat_status_elem.text.strip()

    def _extract_seat_price(self, seat_element) -> str:
        """Extract seat price"""
        try:
            price_elem = seat_element.find_element(By.CSS_SELECTOR, ".bookingclassprice")
            price_text = price_elem.text.strip()
            return price_text.replace('₹', '').strip()
        except:
            return "N/A"