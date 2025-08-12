# Train Ticket Booking API

A FastAPI project that mocks ticket booking system. Currently only supports train ticket booking.

## What it does

- Search for booking train tickets
- Uses Selenium to scrape data from railway websites

## Setup

1. Clone the project
2. Create virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
   ```
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Download ChromeDriver and put it in your PATH
5. Run the app:
   ```bash
   uvicorn main:app --reload
   ```

## Files

- `main.py` - FastAPI app setup
- `transport_scraper.py` - Scraping logic (16KB file)
- `schemas.py` - Data models
- `utils.py` - Helper functions
- `requirements.txt` - Dependencies

## API Usage

### Search Trains

**POST** `/api/availability`

**Request:**
```json
{
  "mode": "train",
  "origin": "palakkad",
  "destination": "thiruvananthapuram",
  "datetime": "2025-08-16"
},
```

**Response:**
```json
{
  "input": {
    "mode": "train",
    "origin": "palakkad",
    "destination": "thiruvananthapuram",
    "datetime": "2025-08-16"
  },
  "schedules": [
    {
      "id": 1,
      "transport_mode": "train",
      "transport_id": "22207",
      "transport_name": "Super AC Express",
      "origin": "Palakkad Jn",
      "departure_time": "00:10",
      "destination": "Trivandrum Central",
      "arrival_time": "07:00",
      "duration": "06 h 50 m",
      "distance": "357 kms",
      "halts": "4 halts",
      "origin_code": "PGT",
      "destination_code": "TVC",
      "seat_availability": [
        {
          "id": 1,
          "class_name": "3A",
          "class_description": "AC 3 Tier",
          "status": "3 Waitlist\nHigh Chance",
          "price": "1040"
        },
        {},
      ]
    },
    {},
    {},
  ],
  "status": "success",
  "message": "Successfully scraped 12 trains"
}
```

## Date Format
Use datetime format:
- `2025-08-16` for 16th August 

**POST** `/api/book`

In the request "seat_number" is experimental
**Request:**
```json
{
  "user_id": "adil",
  "schedule_id": 13,
  "seat_preferences": {
    "seat_class": "SL",
    "seat_position": "upper",
    "coach": "H2",
    "seat_number": "89", 
    "extra": {
      "additionalProp1": {}
    }
  }
}
```

**Response:**
```json
{
  "booking_id": "b46f2381-51a0-48a0-84ff-8cd7852517f2",
  "status": "success",
  "message": "Booking waitlist for Amritha Express (16344) from Palakkad Jn to Trivandrum Central in SL",
  "booking_status": "waitlist"
}
```

**POST** `/api/cancel`

**Request:**
```json
{
  "booking_id": "b46f2381-51a0-48a0-84ff-8cd7852517f2"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Booking cancelled for Amritha Express (16344) from Palakkad Jn to Trivandrum Central"
}
```

**GET** `/api/bookings/{user_id}`
To get all bookings of an user when userid is given

**Response:**
```json
[
  {
    "booking_id": "a496840a-e423-432e-8335-d38ab232ec84",
    "user_id": "adil",
    "schedule_id": 11,
    "booking_status": "cancelled",
    "booking_date": "2025-08-12T10:35:00.574051",
    "seat_preferences": {
      "seat_class": "3A",
      "seat_position": "upper",
      "coach": "H2",
      "seat_number": "89",
      "extra": {
        "additionalProp1": {}
      }
    }
  },
  {},
]
```

**GET** `/api/booking/{booking_id}`
To get details of a particular bookings when booking_id is given

**Response:**
```json
{
  "booking_id": "b46f2381-51a0-48a0-84ff-8cd7852517f2",
  "user_id": "adil",
  "schedule_id": 13,
  "booking_status": "cancelled",
  "booking_date": "2025-08-12T10:55:24.141641",
  "seat_preferences": {
    "seat_class": "SL",
    "seat_position": "upper",
    "coach": "H2",
    "seat_number": "89",
    "extra": {
      "additionalProp1": {}
    }
  },
  "schedule": {
    "id": 13,
    "transport_mode": "train",
    "transport_id": "16344",
    "transport_name": "Amritha Express",
    "origin": "Palakkad Jn",
    "departure_time": "2025-08-16T20:55:00",
    "destination": "Trivandrum Central",
    "arrival_time": "2025-08-17T04:55:00",
    "duration": "08 h 00 m",
    "distance": "371 kms",
    "halts": "14 halts",
    "origin_code": "PGT",
    "destination_code": "TVC",
    "seat_availability": []
  }
}
```

## Notes

- Only train booking works right now
- Need ChromeDriver installed
- Scraping might break if websites change

## Tech Stack

- FastAPI
- Selenium
- Python 3.x

## Future Plans

- Add bus and flight booking 