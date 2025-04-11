"""
Process lecture video information from schools, courses, and lectures.
"""

import sys
from typing import List, Dict, Any
from .search import get_youtube_videos, initialize_driver, close_driver
from selenium import webdriver

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
    
    # Initialize a single WebDriver instance to be reused for all searches
    driver = initialize_driver()
    
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
                    
                    # Search YouTube using the shared driver instance
                    videos = get_youtube_videos(query, max_results=max_results_per_lecture, driver=driver)
                    
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
    finally:
        # Make sure to close the driver when all searches are done
        close_driver(driver)
    
    return lecture_video_list 