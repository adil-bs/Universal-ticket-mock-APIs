from datetime import datetime, timedelta
from typing import Optional, Tuple

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

def extract_day_month_from_date(datetime_str: str) -> Tuple[str, str]:
    """
    Extract day and month name from datetime string for flight calendar selection
    Args:
        datetime_str: Date string in format "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
    Returns:
        Tuple of (day, month_name) - e.g., ("21", "August")
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
        
        # Get full month name
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April', 
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        month = month_names[dt.month]
        
        return day, month
    except Exception as e:
        print(f"Error extracting day/month from {datetime_str}: {e}")
        return "1", "January"

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

def parse_query_date(datetime_str: str) -> tuple[datetime, datetime]:
    """
    Parse query datetime to get start and end of day
    Returns: (start_of_day, end_of_day)
    """
    if ' ' in datetime_str:
        date_part = datetime_str.split(' ')[0]
    else:
        date_part = datetime_str
    
    query_date = datetime.strptime(date_part, '%Y-%m-%d')
    start_of_day = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = query_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_of_day, end_of_day

def normalize_airport_code(location_text: str) -> str:
    """
    Extract airport code from location text
    Examples: "DEL - New Delhi" -> "DEL", "Mumbai (BOM)" -> "BOM"
    """
    try:
        # Handle format: "DEL - New Delhi"
        if ' - ' in location_text:
            return location_text.split(' - ')[0].strip()
        
        # Handle format: "Mumbai (BOM)"
        if '(' in location_text and ')' in location_text:
            start = location_text.find('(') + 1
            end = location_text.find(')')
            return location_text[start:end].strip()
        
        # If already looks like a code (3 uppercase letters)
        if len(location_text) == 3 and location_text.isupper():
            return location_text
        
        # Return first 3 characters as fallback
        return location_text[:3].upper()
    except Exception as e:
        print(f"Error normalizing airport code from {location_text}: {e}")
        return location_text[:3].upper() if location_text else "UNK"

def clean_price_text(price_text: str) -> str:
    """
    Clean price text to extract numeric value
    Examples: "₹42,442" -> "42442", "₹1,234 Extra ₹500 Off" -> "1234"
    """
    try:
        # Remove currency symbols and commas
        cleaned = price_text.replace('₹', '').replace(',', '')
        
        # Extract first numeric sequence
        import re
        numbers = re.findall(r'\d+', cleaned)
        if numbers:
            return numbers[0]
        
        return "0"
    except Exception as e:
        print(f"Error cleaning price text {price_text}: {e}")
        return "0"