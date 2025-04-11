"""
Main entry point for the YouTube embedding application.
"""

import time
import urllib3
from api.client import get_courses_from_api, save_lecture_videos_to_api
from youtube.processor import get_lecture_videos
from utils.scheduler import save_results_to_json, run_scheduled_job

def job():
    """
    Main job function to search for YouTube videos and save them to the API.
    """
    print(f"Starting YouTube video search process... {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get schools on each run (to refresh token)
    current_schools = get_courses_from_api()
    
    if not current_schools:
        print("Could not get schools. Aborting.")
        return
    
    # Search for YouTube videos for all schools and lectures
    print("Searching for YouTube videos for all schools and lectures...")
    
    # Search for max 10 videos per lecture
    lecture_videos = get_lecture_videos(current_schools, max_results_per_lecture=10)
    
    # Show results
    print(f"\nFound a total of {len(lecture_videos)} videos.")
    
    # Save results to API
    if lecture_videos:
        save_result = save_lecture_videos_to_api(lecture_videos)
        if save_result:
            print("Videos successfully saved to API.")
        else:
            print("Error saving videos to API.")
    
    # Optional: Save results to JSON
    save_results_to_json(lecture_videos)
    
    print(f"Process completed. {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # Disable SSL warnings (for development environment)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Run scheduled job
    run_scheduled_job(job) 