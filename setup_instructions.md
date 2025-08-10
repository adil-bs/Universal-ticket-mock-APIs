# Universal Ticketing API Setup Guide

## 1. PostgreSQL Database Setup

### Install PostgreSQL (if not already installed)
- Download from: https://www.postgresql.org/download/
- Follow installation instructions for your OS

### Create Database and User

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database
CREATE DATABASE ticketing_db;

-- Create user (replace 'your_username' and 'your_password')
CREATE USER your_username WITH ENCRYPTED PASSWORD 'your_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ticketing_db TO your_username;

-- Connect to the new database
\c ticketing_db

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO your_username;
```

## 2. Environment Setup

### Create `.env` file in your project root:

```env
# Database Configuration
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/ticketing_db

# Optional: Edge Driver Path (will auto-download if not specified)
# EDGE_DRIVER_PATH=/path/to/your/edgedriver
```

## 3. Install Required Dependencies

```bash
# Install new dependencies
pip install sqlalchemy psycopg2-binary webdriver-manager

# Your existing dependencies should already include:
# fastapi uvicorn selenium pydantic
```

## 4. Directory Structure

```
your_project/
├── main.py                 # Updated FastAPI application
├── database.py            # PostgreSQL database configuration
├── schemas.py             # Updated Pydantic schemas
├── transport_scraper.py   # Unified scraper class
├── utils.py               # Updated booking/cancellation logic
├── .env                   # Environment variables
└── requirements.txt       # Python dependencies
```

## 5. Updated Requirements.txt

```txt
fastapi==0.104.1
uvicorn==0.24.0
selenium==4.15.2
webdriver-manager==4.0.1
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
python-multipart==0.0.6
```

## 6. Database Initialization

The database tables will be created automatically when you run the application for the first time. The tables created are:

1. **transport_schedules** - Main schedules table
2. **seat_availability** - Seat availability linked to schedules
3. **bookings** - User bookings

## 7. API Changes Summary

### Old Endpoints → New Endpoints

| Old | New | Purpose |
|-----|-----|---------|
| `POST /api/availability` | `POST /api/travel/availability` | Get travel availability |
| `POST /api/book` | `POST /api/book` | Book ticket (enhanced) |
| `POST /api/cancel` | `POST /api/cancel` | Cancel ticket (enhanced) |

### New Request/Response Formats

**Travel Availability Request:**
```json
{
    "mode": "train",
    "origin": "New Delhi",
    "destination": "Mumbai",
    "datetime": "2024-01-15",
    "seat_class": "3A"
}
```

**Travel Availability Response:**
```json
{
    "input": {...},
    "schedules": [
        {
            "id": 1,
            "transport_mode": "train",
            "transport_id": "12345",
            "transport_name": "Rajdhani Express",
            "origin": "New Delhi",
            "departure_time": "16:55",
            "destination": "Mumbai",
            "arrival_time": "08:35",
            "duration": "15h 40m",
            "distance": "1384 km",
            "halts": "6 halts",
            "seat_availability": [...]
        }
    ],
    "status": "success",
    "message": "Found 10 schedules from database",
    "source": "database"
}
```

## 8. Key Features

### Database-First Approach
- Searches database first before web scraping
- Saves scraped data for future use
- Reduces scraping frequency and improves response times

### Unified Scraper Architecture
- `TransportScraper` class handles all transport modes
- Easy to extend for bus, flight scrapers
- Consistent data structure across all modes

### Enhanced Booking System
- Complete booking lifecycle management
- UUID-based booking IDs
- Soft delete for cancellations
- Booking history tracking

### Improved Error Handling
- Comprehensive error messages
- Database transaction management
- Graceful fallbacks

## 9. Running the Application

```bash
# Run the FastAPI server
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 10. Testing the API

### Test Travel Availability
```bash
curl -X POST "http://localhost:8000/api/travel/availability" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "train",
    "origin": "New Delhi",
    "destination": "Mumbai",
    "datetime": "2024-01-15",
    "seat_class": "3A"
  }'
```

### Test Booking
```bash
curl -X POST "http://localhost:8000/api/book" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "schedule_id": 1,
    "seat_class": "3A"
  }'
```

### Test Cancellation
```bash
curl -X POST "http://localhost:8000/api/cancel" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "booking-uuid-here"
  }'
```

## 11. Future Enhancements

The architecture is now ready for:
- Bus scraping (`mode: "bus"`)
- Flight scraping (`mode: "flight"`)
- Entertainment domain (movies, concerts)
- Advanced filtering and search
- User management
- Payment integration

## 12. Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check DATABASE_URL in .env file
- Ensure user has proper permissions

### WebDriver Issues
- EdgeChromiumDriverManager will auto-download driver
- Ensure Edge browser is installed
- Check firewall/antivirus settings

### Import Errors
- Verify all dependencies are installed
- Check Python path and virtual environment

This setup provides a robust, scalable foundation for your ticketing API with proper database integration and room for future expansion.