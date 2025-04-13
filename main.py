"""
Main entry point for the YouTube embedding application.
"""

import time
import urllib3
import logging
from api.client import get_courses_from_api, save_lecture_videos_to_api
from youtube.processor import get_lecture_videos
from utils.scheduler import save_results_to_json, run_scheduled_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def job():
    """
    Main job function to search for YouTube videos and save them to the API.
    """
    logger.info(f"Starting YouTube video search process at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get schools on each run (to refresh token)
    current_schools = get_courses_from_api()
    
    if not current_schools:
        logger.error("Could not get schools. Aborting.")
        return
    
    # Search for YouTube videos for all schools and lectures
    logger.info("Searching for YouTube videos for all schools and lectures...")
    
    # Search for max 10 videos per lecture (or use configuration value)
    # reuse_driver=True - tek bir tarayıcı oturumu kullanarak bellek tüketimini azalt
    lecture_videos = get_lecture_videos(
        current_schools, 
        max_results_per_lecture=10,
        reuse_driver=True  # Tek driver kullanarak oturum hatalarını önle
    )
    
    # Show results
    logger.info(f"Found a total of {len(lecture_videos)} videos.")
    
    # Save results to API
    if lecture_videos:
        save_result = save_lecture_videos_to_api(lecture_videos)
        if save_result:
            logger.info("Videos successfully saved to API.")
        else:
            logger.error("Error saving videos to API.")
    
    # Optional: Save results to JSON
    save_results_to_json(lecture_videos)
    
    logger.info(f"Process completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # Disable SSL warnings (for development environment)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Run scheduled job
    run_scheduled_job(job) 