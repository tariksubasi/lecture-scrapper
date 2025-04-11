"""
Configuration settings for the YouTube embedding application.
"""

# API credentials
API_USER = {
    "userName": "cereneryigit",
    "password": "fenerbahce2"
}

# API URLs
API_BASE_URL = "http://localhost:8080"
API_ENDPOINT_TO_GET_COURSES = "/rest/ulug-auth/v1/builder/getSchools-courses-and-lectures"
API_ENDPOINT_TO_AUTHENTICATE = "/rest/ulug-noauth/v1/auth/signin"
API_ENDPOINT_TO_SAVE_LECTURE_VIDEOS = "/rest/ulug-auth/v1/solver/save-lecture-videos"
API_URL_TO_GET_COURSES = API_BASE_URL + API_ENDPOINT_TO_GET_COURSES
API_URL_TO_AUTHENTICATE = API_BASE_URL + API_ENDPOINT_TO_AUTHENTICATE
API_URL_TO_SAVE_LECTURE_VIDEOS = API_BASE_URL + API_ENDPOINT_TO_SAVE_LECTURE_VIDEOS

# YouTube search settings
MAX_RESULTS_PER_LECTURE = 10  # Default max number of videos per lecture
MIN_SCROLLS = 1  # Minimum number of scrolls when searching YouTube
MAX_SCROLLS = 10  # Maximum number of scrolls when searching YouTube

# Schedule settings
SCHEDULE_TIME = "22:08"  # Daily job execution time 