# YouTube Embed Project

A Python application that automatically searches for embeddable YouTube videos related to courses and lectures, and saves them to an API.

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
├── config.py            # Configuration settings
├── main.py              # Main entry point
├── README.md            # This file
└── lecture_videos.json  # Generated output file
```

## Requirements

- Python 3.6+
- Selenium
- Beautiful Soup 4
- Schedule
- Requests
- Chrome/Chromium browser

## Configuration

Edit `config.py` to modify:
- API credentials
- API endpoints
- Schedule settings
- Search parameters

## Usage

Run the application with:

```bash
python main.py
```

The application will:
1. Authenticate with the API
2. Get schools, courses, and lectures information
3. Search YouTube for relevant videos for each lecture
4. Check if videos are embeddable
5. Save videos to API and local JSON file
6. Run on a schedule (default: daily at 02:21)

## How It Works

1. **API Integration**: Authenticates and retrieves course data from backend API
2. **YouTube Search**: Uses Selenium to search YouTube and find videos
3. **Embeddability Check**: Verifies videos can be embedded in web pages
4. **Scheduled Running**: Automatically runs according to the schedule

## Development

To modify the search logic or API integration:
- Edit `youtube/search.py` to change how videos are searched and filtered
- Edit `api/client.py` to modify API communication
- Edit `config.py` to change configuration settings 