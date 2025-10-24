# NYC Cat Tracker - Backend

FastAPI backend for tracking stray cat sightings in NYC.

## Setup

### Local Development with Docker

1. Start the backend and PostgreSQL database:
```bash
docker compose up
```

This will start:
- PostgreSQL database on port 5433 (host) -> 5432 (container)
- FastAPI backend on port 5050
- pgAdmin on port 5051 (optional)

### S3 Image Upload Configuration (Optional)

The backend supports S3 for image uploads. To enable:

1. Create an S3 bucket (e.g., `nyc-cat-tracker-uploads`)
2. Set bucket permissions for public read access
3. Create an IAM user with S3 write permissions
4. Add to `.env`:
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
S3_BUCKET=nyc-cat-tracker-uploads
MAX_UPLOAD_MB=10
```

If S3 credentials are not provided, uploads will fall back to local storage in `/app/uploads`.

### Manual Setup (without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables in `.env`:
```bash
DB_USER=catuser
DB_PASSWORD=catpass
DB_HOST=localhost
DB_PORT=5432
DB_NAME=catdb
PORT=5000
```

3. Run the development server:
```bash
python main.py
```

## API Endpoints

### Cat Sightings
- `GET /api/cats` - Get all cat sightings
- `POST /api/cats` - Create a new cat sighting
- `GET /api/cats/{id}` - Get a specific cat sighting
- `GET /api/cats/recent-with-images` - Get 10 most recent sightings with images

### Uploads
- `POST /api/upload` - Upload an image (returns image URL)

### Reports
- `GET /api/reports/summary` - Get summary statistics
- `GET /api/reports/export` - Export sightings as CSV

### Health
- `GET /` - API info
- `GET /db-test` - Test database connection

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:5000/docs
- ReDoc: http://localhost:5000/redoc

## Database Schema

### cat_sightings
- `id` (Integer, Primary Key)
- `lat` (Float, required)
- `lng` (Float, required)
- `description` (String, required)
- `cat_name` (String, optional)
- `address` (String, optional)
- `image_url` (String, optional)
- `source` (String, default: "map")
- `spotted_at` (DateTime with timezone, defaults to now)
- `created_at` (DateTime with timezone, auto)
- `updated_at` (DateTime with timezone, auto)

