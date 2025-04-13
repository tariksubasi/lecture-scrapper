"""
Configuration settings for the YouTube embedding application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# API credentials
API_USER = {
    "userName": os.environ.get("API_USERNAME", "cereneryigit"),
    "password": os.environ.get("API_PASSWORD", "fenerbahce2")
}

# API URLs
API_BASE_URL = os.environ.get("API_BASE_URL", "https://srv.ulug.io")
API_ENDPOINT_TO_GET_COURSES = "/rest/ulug-auth/v1/builder/getSchools-courses-and-lectures"
API_ENDPOINT_TO_AUTHENTICATE = "/rest/ulug-noauth/v1/auth/signin"
API_ENDPOINT_TO_SAVE_LECTURE_VIDEOS = "/rest/ulug-auth/v1/solver/save-lecture-videos"
API_URL_TO_GET_COURSES = API_BASE_URL + API_ENDPOINT_TO_GET_COURSES
API_URL_TO_AUTHENTICATE = API_BASE_URL + API_ENDPOINT_TO_AUTHENTICATE
API_URL_TO_SAVE_LECTURE_VIDEOS = API_BASE_URL + API_ENDPOINT_TO_SAVE_LECTURE_VIDEOS

# Duration settings in seconds (default values)
SCHEDULER_INTERVAL = int(os.environ.get('SCHEDULER_INTERVAL', 3600))  # 1 hour

# YouTube search settings - optimized for Heroku
MIN_SCROLLS = int(os.environ.get('MIN_SCROLLS', 1))        # Minimum number of scrolls on YouTube (reduced to 1)
MAX_SCROLLS = int(os.environ.get('MAX_SCROLLS', 3))        # Maximum number of scrolls on YouTube (reduced to 3)
MAX_RESULTS_PER_LECTURE = int(os.environ.get('MAX_RESULTS_PER_LECTURE', 5))  # Maximum videos per lecture (reduced to 5)

# Driver settings
DRIVER_TIMEOUT_SECONDS = int(os.environ.get('DRIVER_TIMEOUT_SECONDS', 60))  # Timeout for loading pages
MAX_ATTEMPTS_PER_SEARCH = int(os.environ.get('MAX_ATTEMPTS_PER_SEARCH', 2))  # Max attempts to retry a search

# File paths
DATABASE_FILE = os.environ.get('DATABASE_FILE', 'data/lecture_videos.json')
SCHOOLS_DATA_FILE = os.environ.get('SCHOOLS_DATA_FILE', 'data/schools.json')

# Running type
ENVIRONMENT = os.environ.get('FLASK_ENV', 'production')  # Default is production

# Schedule settings
SCHEDULE_TIME = os.environ.get("SCHEDULE_TIME", "00:40")  # Daily job execution time 