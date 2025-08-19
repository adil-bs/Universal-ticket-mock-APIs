from datetime import datetime, timedelta
from typing import Optional

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