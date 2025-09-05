from datetime import datetime, timedelta
from dateutil.parser import parse
from typing import Optional, Tuple

def datetime_to_ddmm(datetime_str: str) -> str:
    """
    Convert any datetime string (e.g., "YYYY-MM-DD", "YYYY-MM-DD HH:MM:SS", or ISO formats)
    to DDMM format (e.g., "11Aug", "1May").
    """
    try:
        dt = parse(datetime_str)
        return f"{dt.day}{dt.strftime('%b')}"
    except Exception as e:
        print(f"Error converting datetime {datetime_str}: {e}")
        return datetime_str

def extract_day_month_from_date(datetime_str: str) -> tuple[str, str]:
    """
    Extract day and month name from any datetime string for flight calendar selection.
    Args:
        datetime_str: Date string in any reasonable format.
    Returns:
        Tuple of (day, month_name) - e.g., ("21", "August")
    """
    try:
        dt = parse(datetime_str)
        day = str(dt.day)
        month = dt.strftime("%B")  # Full month name via strftime
        return day, month
    except Exception as e:
        print(f"Error extracting day/month from {datetime_str}: {e}")
        return "1", "January"

def time_to_datetime(time_str: str, base_date: str) -> datetime:
    """
    Convert time string (HH:MM) to full datetime using any base_date format.
    Args:
        time_str: Time (e.g. "HH:MM" or with seconds).
        base_date: Any reasonable date string (any format).
    Returns:
        datetime object
    """
    try:
        # Parse the base date robustly
        base_dt = parse(base_date)
        # Parse the time string and update base_dt
        t = parse(time_str)
        # Combine: preserve the original date, update only the time from 'time_str'
        combined_dt = base_dt.replace(
            hour=t.hour,
            minute=t.minute,
            second=t.second if hasattr(t, 'second') else 0,
            microsecond=t.microsecond if hasattr(t, 'microsecond') else 0,
        )
        return combined_dt
    except Exception as e:
        print(f"Error converting time {time_str} with base date {base_date}: {e}")
        # Return just the parsed base date at midnight on failure
        return parse(base_date).replace(hour=0, minute=0, second=0, microsecond=0)

def parse_query_date(datetime_str: str) -> tuple[datetime, datetime]:
    """
    Parse query datetime string to get start and end of day.
    Accepts flexible datetime string formats.
    Returns: (start_of_day, end_of_day)
    """
    # Use dateutil to flexibly parse the string into a datetime
    query_date = parse(datetime_str)
    
    # Normalize to start and end of day
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