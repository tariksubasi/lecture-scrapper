"""
YouTube search functionality to find embeddable videos.
"""

import time
import re
import os
import tempfile
from typing import List, Dict, Any, Set
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import requests
import sys

# Import configuration
sys.path.append('..')
import config

def get_youtube_videos(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Searches YouTube for a specific query, finds embeddable videos and sorts them by view count.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of videos to return
        
    Returns:
        list: List of dictionaries containing video information
    """
    # Configure Chrome settings
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run browser in invisible mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Specify a unique user data directory
    temp_dir = os.path.join(tempfile.gettempdir(), f"chrome_temp_{os.getpid()}")
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    # Additional settings
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        # Start WebDriver using webdriver-manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Go to YouTube search page and search for query (by relevance)
        driver.get("https://www.youtube.com/results?search_query=" + query.replace(" ", "+"))
        # Note: CAMSAhAB parameter removed to use default relevance sorting
        
        # Wait for page to load
        time.sleep(3)
        
        embeddable_videos = []
        processed_video_ids: Set[str] = set()  # Track processed video IDs
        scroll_count = 0
        min_scrolls = config.MIN_SCROLLS
        max_scrolls = config.MAX_SCROLLS
        
        # Loop condition: (Not enough videos AND minimum scroll not reached) OR maximum scroll not reached
        while ((len(embeddable_videos) < max_results and scroll_count < min_scrolls) or scroll_count < max_scrolls):
            # Get page content
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Collect video information
            video_elements = soup.find_all('div', {'id': 'dismissible'})
            
            for element in video_elements:
                # Get video title and ID
                title_element = element.find('a', {'id': 'video-title'})
                if not title_element:
                    continue
                    
                title = title_element.get('title', '')
                if not title:
                    title = title_element.text.strip()
                    
                video_url = title_element.get('href', '')
                if not video_url or not video_url.startswith('/watch?v='):
                    continue
                    
                video_id = video_url.split('v=')[1].split('&')[0]
                
                # Has this video ID already been checked?
                if video_id in processed_video_ids:
                    continue
                
                processed_video_ids.add(video_id)  # Mark ID as processed
                
                # Get view count
                view_count = 0
                
                # Check different HTML structures
                # 1. In new YouTube structure, view info is usually in a span
                view_spans = element.find_all('span', {'class': 'style-scope'})
                for span in view_spans:
                    span_text = span.text.strip()
                    # Check view count formats (1,4 Mn views, 1.4M views, 756 B views, etc.)
                    view_match = re.search(r'([\d,.]+)\s*(?:B|K|M|Mn|bin|milyon|milyar)?\s*(?:görüntüleme|views)', span_text)
                    if view_match:
                        try:
                            # Get the base number first
                            if ',' in view_match.group(1) and '.' not in view_match.group(1):
                                # Turkish format: 1,4 Mn
                                view_base = float(view_match.group(1).replace(',', '.'))
                            else:
                                # English format: 1.4M or plain number: 1400
                                view_base = float(view_match.group(1).replace(',', ''))
                            
                            # Determine multiplier
                            multiplier = 1
                            if 'B ' in span_text or 'bin' in span_text:
                                multiplier = 1000
                            elif 'K' in span_text:
                                multiplier = 1000
                            elif 'M' in span_text or 'Mn' in span_text or 'milyon' in span_text:
                                multiplier = 1000000
                            elif 'milyar' in span_text:
                                multiplier = 1000000000
                            
                            view_count = int(view_base * multiplier)
                            break
                        except ValueError:
                            continue
                
                # 2. Alternatively, check in aria-label
                if view_count == 0:
                    aria_label = title_element.get('aria-label', '')
                    if aria_label:
                        view_match = re.search(r'([\d,.]+)\s*(?:B|K|M|Mn|bin|milyon|milyar)?\s*(?:görüntüleme|views)', aria_label)
                        if view_match:
                            try:
                                # Get the base number first
                                if ',' in view_match.group(1) and '.' not in view_match.group(1):
                                    # Turkish format: 1,4 Mn
                                    view_base = float(view_match.group(1).replace(',', '.'))
                                else:
                                    # English format: 1.4M or plain number: 1400
                                    view_base = float(view_match.group(1).replace(',', ''))
                                
                                # Determine multiplier
                                multiplier = 1
                                if 'B ' in aria_label or 'bin' in aria_label:
                                    multiplier = 1000
                                elif 'K' in aria_label:
                                    multiplier = 1000
                                elif 'M' in aria_label or 'Mn' in aria_label or 'milyon' in aria_label:
                                    multiplier = 1000000
                                elif 'milyar' in aria_label or 'Mr' in aria_label:
                                    multiplier = 1000000000
                                
                                view_count = int(view_base * multiplier)
                            except ValueError:
                                view_count = 0
                
                # 3. Check in metadata
                if view_count == 0:
                    meta_spans = element.find_all('span', {'class': 'inline-metadata-item'})
                    for span in meta_spans:
                        span_text = span.text.strip()
                        view_match = re.search(r'([\d,.]+)\s*(?:B|K|M|Mn|bin|milyon|milyar)?\s*(?:görüntüleme|views)', span_text)
                        if view_match:
                            try:
                                # Get the base number first
                                if ',' in view_match.group(1) and '.' not in view_match.group(1):
                                    # Turkish format: 1,4 Mn
                                    view_base = float(view_match.group(1).replace(',', '.'))
                                else:
                                    # English format: 1.4M or plain number: 1400
                                    view_base = float(view_match.group(1).replace(',', ''))
                                
                                # Determine multiplier
                                multiplier = 1
                                if 'B ' in span_text or 'bin' in span_text:
                                    multiplier = 1000
                                elif 'K' in span_text:
                                    multiplier = 1000
                                elif 'M' in span_text or 'Mn' in span_text or 'milyon' in span_text:
                                    multiplier = 1000000
                                elif 'milyar' in span_text or 'Mr' in span_text:
                                    multiplier = 1000000000
                                
                                view_count = int(view_base * multiplier)
                                break
                            except ValueError:
                                continue
                
                # Check embeddability immediately
                if check_embeddable(video_id):
                    video_info = {
                        'title': title,
                        'video_id': video_id,
                        'view_count': view_count,
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'watch_url': f'https://www.youtube.com/watch?v={video_id}'
                    }
                    embeddable_videos.append(video_info)
                    print(f"Found embeddable video ({len(embeddable_videos)}/{max_results}): {title}")
            
            # Scroll down to load more videos
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
            time.sleep(2)
            scroll_count += 1
            print(f"Page scrolled ({scroll_count}/{max_scrolls}), found {len(embeddable_videos)} embeddable videos so far.")
            
            # Check if we've scrolled the minimum number of times and found enough videos
            if scroll_count >= min_scrolls and len(embeddable_videos) >= max_results:
                print(f"Exceeded minimum scroll count ({min_scrolls}) and found enough videos ({len(embeddable_videos)}). Stopping.")
                break
                
        # Sort results by view count
        embeddable_videos.sort(key=lambda x: x['view_count'], reverse=True)
        return embeddable_videos[:max_results]  # Return only the requested number of videos
        
    except Exception as e:
        print(f"Error while starting WebDriver: {str(e)}")
        return []
        
    finally:
        try:
            driver.quit()
        except:
            pass
        
        # Try to clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def check_embeddable(video_id: str) -> bool:
    """
    Checks if a video is embeddable.
    
    Args:
        video_id (str): YouTube video ID
        
    Returns:
        bool: True if video is embeddable, False otherwise
    """
    try:
        # Make direct request to embed URL and check status code
        embed_url = f'https://www.youtube.com/embed/{video_id}'
        response = requests.get(embed_url, timeout=5, allow_redirects=True)
        
        # 401 Unauthorized or other error codes mean not embeddable
        if response.status_code != 200:
            print(f"Video ID {video_id} not embeddable. HTTP status code: {response.status_code}")
            return False
            
        # Check response content for "Video unavailable" or similar phrases
        if "Video unavailable" in response.text or "UNPLAYABLE" in response.text:
            print(f"Video ID {video_id} not embeddable. Content unavailable.")
            return False
            
        # Additional check: also use oEmbed API
        oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
        oembed_response = requests.get(oembed_url, timeout=5)
        
        if oembed_response.status_code != 200:
            print(f"oEmbed API error for Video ID {video_id}: {oembed_response.status_code}")
            return False
            
        return True
    except Exception as e:
        print(f"Error during embed check for Video ID {video_id}: {str(e)}")
        return False 