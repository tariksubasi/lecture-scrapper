"""
Process lecture video information from schools, courses, and lectures.
"""

import sys
import time
from typing import List, Dict, Any
from .search import get_youtube_videos, shutdown_driver

# Import configuration
sys.path.append('..')
import config

def get_lecture_videos(schools: List[Dict[str, Any]], max_results_per_lecture: int = None) -> List[Dict[str, Any]]:
    """
    Searches for YouTube videos for all schools, courses, and lectures and collects the results.
    
    Args:
        schools (list): List containing school, course, and lecture information
        max_results_per_lecture (int): Maximum number of videos to search for per lecture
        
    Returns:
        list: List of lecture videos
    """
    # Use configuration default if not provided
    if max_results_per_lecture is None:
        max_results_per_lecture = config.MAX_RESULTS_PER_LECTURE
        
    lecture_video_list = []
    error_count = 0
    max_errors = 3
    
    try:
        for school in schools:
            school_type = school.get("schoolType", "")
            
            for course in school["Courses"]:
                course_name = course["courseName"]
                
                for lecture in course["Lectures"]:
                    lecture_id = lecture["lectureId"]
                    lecture_name = lecture["lectureName"]
                    
                    # Create search query - can include school type
                    query = f"{school_type} - {course_name} - {lecture_name}"
                    print(f"\nSearching for: {query}")
                    
                    # Search YouTube with retries
                    try:
                        videos = get_youtube_videos(query, max_results=max_results_per_lecture)
                        # Add results to list
                        for video in videos:
                            video_info = {
                                "lectureId": lecture_id,
                                "videoName": video["title"],
                                "youtubeVideoID": video["video_id"],
                                "url": video["watch_url"],
                                "embedUrl": video["embed_url"],
                                "viewCount": video["view_count"]
                            }
                            lecture_video_list.append(video_info)
                            
                        print(f"Found {len(videos)} videos for {lecture_name}.")
                        
                        # Reset error count on successful search
                        error_count = 0
                        
                    except Exception as e:
                        print(f"Error searching for videos for {lecture_name}: {str(e)}")
                        error_count += 1
                        
                        # If we've had too many errors in a row, we should stop
                        if error_count >= max_errors:
                            print(f"Too many consecutive errors ({error_count}). Stopping search.")
                            return lecture_video_list
                        
                        # Wait a bit before trying the next lecture
                        time.sleep(5)
        
        return lecture_video_list
        
    finally:
        # Ensure WebDriver is closed properly when done
        shutdown_driver() 