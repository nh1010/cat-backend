# NYC Cat Tracker - Backend

FastAPI backend for tracking stray cat sightings in NYC.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection string
```

3. Run the development server:
```bash
python src/main.py
```

Or using uvicorn directly:
```bash
uvicorn src.main:app --reload --port 5000
```

## API Endpoints

- `GET /` - API info
- `GET /db-test` - Test database connection
- `GET /api/cats` - Get all cat sightings
- `POST /api/cats` - Create a new cat sighting
- `GET /api/cats/{id}` - Get a specific cat sighting

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:5000/docs
- ReDoc: http://localhost:5000/redoc

## Database Schema

### cat_sightings
- `id` (Integer, Primary Key)
- `lat` (Float)
- `lng` (Float)
- `description` (String)
- `reported_at` (DateTime with timezone)

