# Docker Setup for Arrow Configuration Calculator

This directory contains Docker configuration files for containerizing the Arrow Configuration Calculator web application.

## Quick Start

### Using Docker Compose (Recommended)

1. Build and run the container:
```bash
docker-compose up -d
```

2. Access the application at: http://localhost:5001

3. Stop the container:
```bash
docker-compose down
```

### Using Docker Directly

1. Build the Docker image:
```bash
docker build -t arrow-calculator .
```

2. Run the container:
```bash
docker run -d -p 5001:5001 --name arrow-calculator arrow-calculator
```

3. Stop the container:
```bash
docker stop arrow-calculator
docker rm arrow-calculator
```

## Production Deployment

For production deployment, use the optimized multi-stage Dockerfile:

```bash
docker build -f Dockerfile.prod -t arrow-calculator:prod .
docker run -d -p 5001:5001 --name arrow-calculator arrow-calculator:prod
```

## Environment Variables

- `PORT`: Port number for the application (default: 5001)
- `FLASK_ENV`: Flask environment (development/production)

## Files

- `Dockerfile`: Standard development Dockerfile
- `Dockerfile.prod`: Multi-stage production Dockerfile with Gunicorn
- `docker-compose.yml`: Docker Compose configuration
- `.dockerignore`: Files to exclude from Docker build context

## Notes

- The application uses the Plotly version (`app_plotly.py`) by default
- Data files (CSV) are included in the container
- The production build uses Gunicorn with 4 workers for better performance
- Health checks are configured in docker-compose.yml