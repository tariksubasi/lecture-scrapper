# YouTube Embed Project

A Python Flask application that automatically searches for embeddable YouTube videos related to courses and lectures, and saves them to an API. Can be deployed to Heroku.

## Project Structure

```
youtube-embed/
├── api/                 # API interaction modules
│   ├── __init__.py
│   └── client.py        # API client functions
├── youtube/             # YouTube search functionality
│   ├── __init__.py
│   ├── search.py        # YouTube video search and embed check
│   └── processor.py     # Process lecture videos
├── utils/               # Utility functions
│   ├── __init__.py
│   └── scheduler.py     # Scheduling functionality
├── app.py               # Flask application
├── config.py            # Configuration settings
├── Procfile             # Heroku process file
├── runtime.txt          # Python runtime for Heroku
├── requirements.txt     # Dependencies
├── .env.example         # Example environment variables
└── lecture_videos.json  # Generated output file
```

## Requirements

- Python 3.6+
- Flask
- Selenium
- Beautiful Soup 4
- Schedule
- Requests
- Chrome/Chromium browser
- Gunicorn (for production deployment)

## Configuration

Configuration is done through environment variables. Copy `.env.example` to `.env` and edit the values.

Available environment variables:
- `API_USERNAME` - Username for API authentication
- `API_PASSWORD` - Password for API authentication
- `API_BASE_URL` - Base URL for the API
- `MAX_RESULTS_PER_LECTURE` - Maximum number of videos to search for per lecture
- `MIN_SCROLLS` - Minimum number of scrolls when searching YouTube
- `MAX_SCROLLS` - Maximum number of scrolls when searching YouTube
- `SCHEDULE_TIME` - Time to run the scheduled job (format: "HH:MM")

## Local Usage

Run the application locally with:

```bash
python app.py
```

The Flask application will start on http://localhost:5000 with the following endpoints:
- `/` - Home page with endpoint information
- `/status` - Get the status of the last job
- `/run` - Trigger a new job (POST request)
- `/api/courses` - Get courses from the API
- `/api/videos` - Get found videos

## Heroku Deployment

1. Create a Heroku account if you don't have one
2. Install the Heroku CLI
3. Login to Heroku:
   ```bash
   heroku login
   ```
4. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```
5. Set environment variables:
   ```bash
   heroku config:set API_USERNAME=your_username
   heroku config:set API_PASSWORD=your_password
   heroku config:set API_BASE_URL=http://your-api-url.com
   ```
6. Add buildpacks for Chrome and Python:
   ```bash
   heroku buildpacks:add https://github.com/heroku/heroku-buildpack-google-chrome
   heroku buildpacks:add heroku/python
   ```
7. Deploy the application:
   ```bash
   git push heroku main
   ```

### Heroku Considerations

- The free tier of Heroku has limitations on dyno hours and may not be suitable for continuous operation
- For the YouTube search functionality that requires Selenium, additional configuration may be needed
- Consider using Heroku Scheduler add-on for periodic jobs instead of the built-in scheduler

## How It Works

1. **API Integration**: Authenticates and retrieves course data from backend API
2. **YouTube Search**: Uses Selenium to search YouTube and find videos
3. **Embeddability Check**: Verifies videos can be embedded in web pages
4. **REST API**: Exposes endpoints to trigger searches and retrieve results 