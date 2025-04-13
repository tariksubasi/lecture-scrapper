"""
YouTube search functionality to find embeddable videos.
"""

import time
import re
import os
import tempfile
import glob
import platform
import logging
import gc
import sys
import subprocess
import requests
from typing import List, Dict, Any, Set, Optional

# Önce logging kurulumu yap
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import configuration
sys.path.append('..')
import config

# 3rd party imports için undetected_chromedriver importu önce yapılmalı
try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, 
        WebDriverException, 
        InvalidSessionIdException, 
        NoSuchElementException, 
        StaleElementReferenceException
    )
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    raise

def get_chrome_version(chrome_binary):
    """
    Get the version of Chrome from the binary.
    
    Args:
        chrome_binary (str): Path to Chrome binary
        
    Returns:
        str: Chrome version or None if not found
    """
    try:
        if platform.system() == "Windows":
            # Windows method - use WMIC
            # Fix f-string backslash issue
            path_for_cmd = chrome_binary.replace("\\", "\\\\")
            cmd = 'wmic datafile where name="' + path_for_cmd + '" get Version /value'
            output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if "Version=" in output:
                return output.split("=")[1]
        else:
            # Linux/Mac method - use Chrome --version
            cmd = [chrome_binary, '--version']
            output = subprocess.check_output(cmd).decode('utf-8').strip()
            # Extract version number (e.g., "Google Chrome 135.0.7049.84" -> "135.0.7049.84")
            if "Chrome" in output:
                version = re.search(r'Chrome\s+(\d+\.\d+\.\d+\.\d+)', output)
                if version:
                    return version.group(1)
    except Exception as e:
        logger.error(f"Failed to get Chrome version: {e}")
    
    return None

def initialize_driver() -> webdriver.Chrome:
    """
    Initialize and configure a Chrome WebDriver for YouTube searches.
    Optimized for Heroku deployment. Uses undetected-chromedriver for better compatibility.
    
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    logger.info("Initializing new Chrome WebDriver with undetected-chromedriver")
    temp_dir = tempfile.mkdtemp()
    
    # Yapılandırma seçenekleri
    chrome_options = uc.ChromeOptions()
    
    # Temel seçenekler
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    
    # Bellek optimizasyonları
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins-discovery")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    # Bellek optimizasyonları
    chrome_options.add_argument("--js-flags=--expose-gc")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Sayfa yükleme stratejisi
    chrome_options.page_load_strategy = 'eager'
    
    try:
        # Önce Heroku ortamında Chrome'u tespit etmeye çalış
        if 'GOOGLE_CHROME_BIN' in os.environ:
            chrome_binary = os.environ.get('GOOGLE_CHROME_BIN')
            logger.info(f"Using Chrome binary from GOOGLE_CHROME_BIN: {chrome_binary}")
            chrome_options.binary_location = chrome_binary
        
        # undetected_chromedriver kullanarak driver oluştur
        # Bu yöntem ChromeDriver ve Chrome arasındaki uyumsuzluğu otomatik olarak çözer
        driver = uc.Chrome(options=chrome_options)
        
        # Zaman aşımı ayarları
        driver.set_page_load_timeout(config.DRIVER_TIMEOUT_SECONDS)
        
        logger.info("Chrome WebDriver initialized successfully with undetected-chromedriver")
        return driver
    
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {str(e)}")
        # Driver oluşturulamazsa geçici dizini temizle
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        raise

def cleanup_memory():
    """
    Force garbage collection and memory cleanup
    """
    gc.collect()

def clear_browser_data(driver):
    """
    Clear browser cache, cookies, and other storage to free up memory.
    
    Args:
        driver (WebDriver): The WebDriver instance to clean
    """
    if not driver:
        return
        
    try:
        # Check if driver session is valid first
        try:
            # Just check if we can access a property - will raise exception if invalid 
            _ = driver.current_url
        except (InvalidSessionIdException, WebDriverException):
            print("Session already invalid, skipping data clearing")
            return
            
        # Clear various browser storage mechanisms with timeout protection
        try:
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            driver.delete_all_cookies()
            driver.execute_script("if (window.gc) window.gc();")
            print("Browser data cleared")
        except Exception as e:
            print(f"Error during browser data clearing: {e}")
            
    except Exception as e:
        print(f"Error clearing browser data: {e}")

def close_driver(driver: Optional[webdriver.Chrome]) -> None:
    """
    Safely close the WebDriver instance and clean up resources.
    
    Args:
        driver: Chrome WebDriver instance to close
    """
    if driver:
        try:
            logger.info("Closing WebDriver")
            driver.quit()
        except Exception as e:
            logger.warning(f"Error while closing driver: {str(e)}")
        
        # Force garbage collection
        try:
            import gc
            gc.collect()
        except:
            pass

def get_youtube_videos(query: str, max_results: int = 15, driver: Optional[webdriver.Chrome] = None) -> List[Dict[str, Any]]:
    """
    Search YouTube for videos matching the given query.
    Can reuse an existing driver or create a new one if not provided.
    
    Args:
        query: YouTube search query
        max_results: Maximum number of results to return (default: 15)
        driver: Optional existing WebDriver instance to reuse
    
    Returns:
        List of dictionaries containing video info (title, url, duration, etc.)
    """
    results = []
    attempts = 0
    max_attempts = config.MAX_ATTEMPTS_PER_SEARCH
    should_close_driver = False
    
    while attempts < max_attempts and not results:
        attempts += 1
        try:
            # Initialize driver only if not provided
            if driver is None:
                driver = initialize_driver()
                should_close_driver = True
            
            # Perform the search
            logger.info(f"Searching YouTube for: {query} (attempt {attempts}/{max_attempts})")
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            driver.get(search_url)
            
            # Wait for the search results to load
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.ID, "contents")))
            
            # Scroll to load more videos (reduced scrolling for reliability)
            scroll_count = config.MIN_SCROLLS
            max_scrolls = min(config.MAX_SCROLLS, (max_results // 5) + 1)  # Estimate scrolls needed
            
            logger.info(f"Scrolling to load more videos (max: {max_scrolls})")
            while scroll_count < max_scrolls:
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)  # Brief pause to allow content to load
                scroll_count += 1
            
            # Extract video elements
            time.sleep(2)  # Extra wait to ensure videos are loaded
            video_elements = driver.find_elements(By.CSS_SELECTOR, "#dismissible.ytd-video-renderer")
            
            logger.info(f"Found {len(video_elements)} video elements")
            
            # Process each video element
            for element in video_elements[:max_results]:
                try:
                    # Extract video title and URL
                    title_element = element.find_element(By.CSS_SELECTOR, "#video-title")
                    title = title_element.get_attribute("title")
                    url = title_element.get_attribute("href")
                    
                    # Only include embeddable YouTube videos
                    if url and "/watch?v=" in url:
                        video_id = url.split("v=")[1].split("&")[0]
                        
                        # Extract duration if available
                        try:
                            duration = element.find_element(By.CSS_SELECTOR, ".ytd-thumbnail-overlay-time-status-renderer").text.strip()
                        except NoSuchElementException:
                            duration = "Unknown"
                        
                        # Extract channel name if available
                        try:
                            channel = element.find_element(By.CSS_SELECTOR, ".yt-simple-endpoint.style-scope.yt-formatted-string").text
                        except NoSuchElementException:
                            channel = "Unknown"
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "videoId": video_id,
                            "duration": duration,
                            "channel": channel,
                            "embeddable": True
                        })
                except (NoSuchElementException, StaleElementReferenceException) as e:
                    logger.warning(f"Error extracting video info: {str(e)}")
                    continue
            
            logger.info(f"Successfully extracted {len(results)} videos")
            
        except TimeoutException:
            logger.warning(f"Timeout while searching YouTube (attempt {attempts}/{max_attempts})")
        except InvalidSessionIdException:
            logger.warning(f"Invalid session ID error (attempt {attempts}/{max_attempts})")
        except WebDriverException as e:
            logger.warning(f"WebDriver error: {str(e)} (attempt {attempts}/{max_attempts})")
        except Exception as e:
            logger.error(f"Unexpected error during YouTube search: {str(e)}")
        finally:
            # Only close the driver if we created it in this function
            if should_close_driver:
                close_driver(driver)
                driver = None
    
    return results[:max_results]

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
        # Add timeout to prevent hanging
        response = requests.get(embed_url, timeout=5, allow_redirects=True)
        
        # 401 Unauthorized or other error codes mean not embeddable
        if response.status_code != 200:
            print(f"Video ID {video_id} not embeddable. HTTP status code: {response.status_code}")
            return False
            
        # Check response content for "Video unavailable" or similar phrases
        content = response.text.lower()
        unavailable_phrases = ["video unavailable", "unplayable", "not available", "video was removed"]
        for phrase in unavailable_phrases:
            if phrase in content:
                print(f"Video ID {video_id} not embeddable. Content unavailable.")
                return False
            
        return True
        
    except requests.RequestException as e:
        print(f"Error during embed check for Video ID {video_id}: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error checking Video ID {video_id}: {str(e)}")
        return False 