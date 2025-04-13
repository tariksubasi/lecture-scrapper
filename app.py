"""
Flask application for YouTube embedding service.
"""

import os
import json
import subprocess
import logging
import threading
import time
import schedule
import config
import glob

from flask import Flask, jsonify, request
from api.client import get_courses_from_api, save_lecture_videos_to_api
from youtube.processor import get_lecture_videos
from utils.scheduler import save_results_to_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variable to store the last job result
last_job_result = {
    "status": "No job run yet",
    "timestamp": None,
    "video_count": 0
}

# Flag to prevent multiple jobs running simultaneously
job_running = False
job_lock = threading.Lock()

def job():
    """
    Main job function to search for YouTube videos and save them to the API.
    """
    global last_job_result, job_running
    
    with job_lock:
        if job_running:
            logger.warning("Job already running, skipping...")
            return
        job_running = True
    
    try:
        start_time = time.strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Starting YouTube video search process at {start_time}")
        
        # Get schools on each run (to refresh token)
        current_schools = get_courses_from_api()
        
        if not current_schools:
            last_job_result = {
                "status": "Error: Could not get schools",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "video_count": 0
            }
            return
        
        # Search for YouTube videos for all schools and lectures
        logger.info("Searching for YouTube videos for all schools and lectures...")
        
        # Search for videos per lecture with shared driver
        lecture_videos = get_lecture_videos(
            current_schools, 
            max_results_per_lecture=config.MAX_RESULTS_PER_LECTURE,
            reuse_driver=True  # Tek driver kullanarak performansı artır ve oturum hatalarını önle
        )
        
        # Show results
        logger.info(f"Found a total of {len(lecture_videos)} videos.")
        
        # Save results to API
        if lecture_videos:
            save_result = save_lecture_videos_to_api(lecture_videos)
            status = "Success" if save_result else "Error saving to API"
        else:
            status = "No videos found"
            
        # Optional: Save results to JSON
        save_results_to_json(lecture_videos)
        
        last_job_result = {
            "status": status,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "video_count": len(lecture_videos)
        }
        
        logger.info(f"Process completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"Error in job: {str(e)}")
        last_job_result = {
            "status": f"Error: {str(e)}",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "video_count": 0
        }
    finally:
        with job_lock:
            job_running = False

def scheduler_thread():
    """
    Background thread that runs the scheduler.
    """
    schedule_time = config.SCHEDULE_TIME
    schedule.every().day.at(schedule_time).do(job)
    
    logger.info(f"YouTube video search service started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Will run automatically every day at {schedule_time}.")
    
    # Check for first run
    current_hour = time.localtime().tm_hour
    current_min = time.localtime().tm_min
    schedule_hour = int(schedule_time.split(':')[0])
    schedule_min = int(schedule_time.split(':')[1])
    
    if current_hour == schedule_hour and current_min >= schedule_min and current_min < schedule_min + 2:
        logger.info("Matched start time, running immediately...")
        job()
    
    # Infinite loop to check scheduler
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
            # Wait 5 minutes and try again on error
            time.sleep(300)

@app.route('/')
def home():
    return jsonify({
        "service": "YouTube Embed API",
        "status": "running",
        "endpoints": [
            "/status - Get the status of the last job",
            "/run - Trigger a new job",
            "/api/courses - Get courses from the API",
            "/api/videos - Get found videos",
            "/diagnostics - Get system diagnostics"
        ]
    })

@app.route('/status')
def status():
    return jsonify(last_job_result)

@app.route('/run', methods=['POST'])
def trigger_job():
    # Start the job in a separate thread to avoid blocking the request
    thread = threading.Thread(target=job)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "Job started", "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/api/courses')
def get_courses():
    courses = get_courses_from_api()
    if courses:
        return jsonify(courses)
    return jsonify({"error": "Could not get courses"}), 500

@app.route('/api/videos')
def get_videos():
    try:
        with open("lecture_videos.json", "r") as f:
            videos = json.load(f)
        return jsonify(videos)
    except Exception as e:
        return jsonify({"error": f"Could not get videos: {str(e)}"}), 500

@app.route('/diagnostics')
def diagnostics():
    """
    Get system diagnostics, useful for troubleshooting Chrome/Selenium issues
    """
    diagnostics_info = {}
    
    # Check for Chrome in possible locations
    chrome_locations = [
        '/app/.chrome/chrome/chrome',
        '/app/.apt/usr/bin/google-chrome',
        '/app/.apt/opt/google/chrome/chrome',
        '/app/.heroku/google-chrome/bin/chrome',
        '/app/.chrome-for-testing/chrome-linux64/chrome'
    ]
    
    chrome_locations_status = {}
    for location in chrome_locations:
        chrome_locations_status[location] = os.path.exists(location)
    
    diagnostics_info['chrome_locations'] = chrome_locations_status
    
    # Search for Chrome in the filesystem
    try:
        chrome_paths_found = glob.glob('/app/**/*chrome*', recursive=True)
        diagnostics_info['chrome_paths_found'] = chrome_paths_found
    except Exception as e:
        diagnostics_info['chrome_paths_found_error'] = str(e)
    
    # Check environment variables
    env_vars = {}
    for var in ['GOOGLE_CHROME_BIN', 'GOOGLE_CHROME_SHIM', 'CHROME_EXECUTABLE_PATH', 'PATH']:
        env_vars[var] = os.environ.get(var, 'Not set')
    
    diagnostics_info['environment_variables'] = env_vars
    
    # Check Chrome version if available
    try:
        for chrome_path in chrome_locations:
            if os.path.exists(chrome_path):
                chrome_version = subprocess.check_output([chrome_path, '--version'], stderr=subprocess.STDOUT).decode().strip()
                diagnostics_info['chrome_version'] = chrome_version
                break
    except Exception as e:
        diagnostics_info['chrome_version_error'] = str(e)
    
    # Check buildpacks
    try:
        buildpacks = subprocess.check_output(['heroku', 'buildpacks', '--app', os.environ.get('HEROKU_APP_NAME', '')], stderr=subprocess.STDOUT).decode().strip()
        diagnostics_info['buildpacks'] = buildpacks
    except Exception as e:
        diagnostics_info['buildpacks_error'] = str(e)
    
    return jsonify(diagnostics_info)

# Start the scheduler in a background thread when the app starts
def start_scheduler():
    thread = threading.Thread(target=scheduler_thread)
    thread.daemon = True
    thread.start()

# Start the scheduler when the app is initialized
start_scheduler()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 