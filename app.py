"""
Flask application for YouTube embedding service.
"""

import os
import json
from flask import Flask, jsonify, request
from api.client import get_courses_from_api, save_lecture_videos_to_api
from youtube.processor import get_lecture_videos
from utils.scheduler import save_results_to_json
import threading
import time
import schedule
import config

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
            print("Job already running, skipping...")
            return
        job_running = True
    
    try:
        start_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"Starting YouTube video search process... {start_time}")
        
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
        print("Searching for YouTube videos for all schools and lectures...")
        
        # Search for videos per lecture
        lecture_videos = get_lecture_videos(current_schools, max_results_per_lecture=10)
        
        # Show results
        print(f"\nFound a total of {len(lecture_videos)} videos.")
        
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
        
        print(f"Process completed. {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        last_job_result = {
            "status": f"Error: {str(e)}",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "video_count": 0
        }
        print(f"Error in job: {str(e)}")
    finally:
        with job_lock:
            job_running = False

def scheduler_thread():
    """
    Background thread that runs the scheduler.
    """
    schedule_time = config.SCHEDULE_TIME
    schedule.every().day.at(schedule_time).do(job)
    
    print(f"YouTube video search service started. {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Will run automatically every day at {schedule_time}.")
    
    # Check for first run
    # current_hour = time.localtime().tm_hour
    # current_min = time.localtime().tm_min
    # schedule_hour = int(schedule_time.split(':')[0])
    # schedule_min = int(schedule_time.split(':')[1])
    
    # if current_hour == schedule_hour and current_min >= schedule_min and current_min < schedule_min + 2:
    #     print("Matched start time, running immediately...")
        #job()
    
    # Infinite loop to check scheduler
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Scheduler error: {str(e)}")
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
            "/api/videos - Get found videos"
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