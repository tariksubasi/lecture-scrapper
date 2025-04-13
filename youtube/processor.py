"""
Process lecture video information from schools, courses, and lectures.
"""

import sys
import time
import logging
from typing import List, Dict, Any, Optional
from .search import get_youtube_videos, initialize_driver, close_driver
from selenium import webdriver

# Import configuration
sys.path.append('..')
import config

# Set up logger
logger = logging.getLogger(__name__)

def get_lecture_videos(schools: List[Dict[str, Any]], max_results_per_lecture: int = None, reuse_driver: bool = True) -> List[Dict[str, Any]]:
    """
    Searches for YouTube videos for all schools, courses, and lectures and collects the results.
    
    Args:
        schools (list): List containing school, course, and lecture information
        max_results_per_lecture (int): Maximum number of videos to search for per lecture
        reuse_driver (bool): Whether to reuse the same driver for all searches
        
    Returns:
        list: List of lecture videos
    """
    # Use configuration default if not provided
    if max_results_per_lecture is None:
        max_results_per_lecture = config.MAX_RESULTS_PER_LECTURE
        
    lecture_video_list = []
    
    # Driver yeniden kullanımı veya her arama için yeni driver oluşturma
    shared_driver = None
    
    try:
        # Eğer driver yeniden kullanılacaksa, paylaşılan bir driver oluştur
        if reuse_driver:
            logger.info("Initializing shared driver for all searches")
            shared_driver = initialize_driver()
    
        for school in schools:
            school_type = school.get("schoolType", "")
            
            for course in school["Courses"]:
                course_name = course["courseName"]
                
                for lecture in course["Lectures"]:
                    lecture_id = lecture["lectureId"]
                    lecture_name = lecture["lectureName"]
                    
                    # Create search query - can include school type
                    query = f"{school_type} - {course_name} - {lecture_name}"
                    logger.info(f"Searching for: {query}")
                    
                    # Try with retry logic
                    success = False
                    max_retries = 2
                    
                    for attempt in range(max_retries):
                        try:
                            # Eğer paylaşılan driver kullanıyorsak ve bir hata oluştuysa yeniden oluştur
                            if reuse_driver and shared_driver is None:
                                shared_driver = initialize_driver()
                                
                            # Paylaşılan driver veya her seferinde yeni driver oluştur
                            current_driver = shared_driver if reuse_driver else None
                            
                            # Perform YouTube search
                            videos = get_youtube_videos(
                                query, 
                                max_results=max_results_per_lecture, 
                                driver=current_driver
                            )
                            
                            # Add results to list
                            for video in videos:
                                # Alan adlarını normalize et (videoId yerine video_id gibi)
                                video_id = video.get("video_id") or video.get("videoId")
                                if not video_id:
                                    logger.warning(f"Skipping video without ID: {video.get('title')}")
                                    continue
                                    
                                # API'ye gönderilecek video bilgilerini formatla
                                video_info = {
                                    "lectureId": lecture_id,
                                    "videoName": video.get("title"),
                                    "youtubeVideoID": video_id,
                                    "url": video.get("watch_url") or video.get("url"),
                                    "embedUrl": video.get("embed_url") or f"https://www.youtube.com/embed/{video_id}",
                                    "viewCount": video.get("view_count", 0)
                                }
                                lecture_video_list.append(video_info)
                            
                            logger.info(f"Found {len(videos)} videos for {lecture_name}.")
                            success = True
                            break
                            
                        except Exception as e:
                            logger.error(f"Error searching for videos for {lecture_name} (attempt {attempt+1}/{max_retries}): {str(e)}")
                            
                            # Driver hatalıysa, paylaşılan driver'ı yeniden oluştur
                            if reuse_driver:
                                try:
                                    if shared_driver:
                                        close_driver(shared_driver)
                                except:
                                    pass
                                shared_driver = None
                                time.sleep(2)  # Driver yeniden oluşturmadan önce kısa bir bekleme
                    
                    # Tüm denemeler başarısız olduysa log oluştur
                    if not success:
                        logger.error(f"Failed to search for videos for {lecture_name} after {max_retries} attempts")
                    
                    # Aramalar arasında bellek temizliği yap
                    import gc
                    gc.collect()
                    
                    # Aramalar arasında küçük bir bekleme ekle
                    time.sleep(1)
    
    finally:
        # Paylaşılan driver kullanıyorsak, işlem bittiğinde kapat
        if reuse_driver and shared_driver:
            logger.info("Closing shared driver")
            close_driver(shared_driver)
    
    return lecture_video_list 