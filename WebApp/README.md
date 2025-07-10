# Arrow Spine Calculator Web App

A web application for calculating optimal arrow configurations based on bow and arrow specifications.

## Features

- Interactive sliders for all arrow and bow parameters
- Real-time calculations of:
  - Optimal point weight
  - Total arrow mass
  - Front of Center (FOC) percentage
  - Arrow velocity (FPS) at different distances
  - Kinetic energy with game-type bands
  - Momentum
- Visual plots showing relationships between poundage and calculated values
- Physics-based drag modeling for velocity calculations

## Local Development

1. Install dependencies:
```bash
cd WebApp
pip install -r requirements.txt
```

2. Run the development server:
```bash
python app.py
```

3. Open http://localhost:5000 in your browser

## Deployment Options

### Option 1: Using Gunicorn (Recommended for Production)

```bash
# Install gunicorn if not already installed
pip install gunicorn

# Run with gunicorn (4 workers)
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### Option 2: Deploy to a VPS/Cloud Server

1. Clone the repository to your server
2. Install Python 3.8+ and pip
3. Install dependencies: `pip install -r requirements.txt`
4. Configure a reverse proxy (nginx/Apache) to forward requests to Gunicorn
5. Set up a systemd service or supervisor to keep the app running

Example nginx configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Option 3: Deploy to Heroku

1. Create a `Procfile` in the WebApp directory:
```
web: gunicorn wsgi:app
```

2. Deploy to Heroku:
```bash
heroku create your-app-name
git push heroku main
```

### Option 4: Deploy to PythonAnywhere

1. Upload the WebApp folder to PythonAnywhere
2. Create a new web app
3. Set the source code directory to your WebApp folder
4. Configure the WSGI file to import from `app`

### Option 5: Deploy as Static Site with Serverless Backend

For lower hosting costs, you can:
1. Host the HTML/CSS/JS on any static hosting (GitHub Pages, Netlify, Vercel)
2. Deploy the Flask API as a serverless function (AWS Lambda, Vercel Functions, Netlify Functions)

## Environment Variables

For production, you may want to set:
- `FLASK_ENV=production`
- `SECRET_KEY=your-secret-key` (if adding authentication later)

## Data Files

The app requires two CSV files in the same directory as `app.py`:
- `ArrowSpine3.csv` - Arrow spine data
- `ArrowGPIs.csv` - Arrow GPI (grains per inch) data

## Browser Compatibility

The app works on modern browsers that support:
- ES6 JavaScript
- CSS Grid
- Bokeh.js visualization library

Tested on Chrome, Firefox, Safari, and Edge.