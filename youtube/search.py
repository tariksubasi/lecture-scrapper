"""
YouTube search functionality to find embeddable videos.
"""

import time
import re
import os
import tempfile
import glob
import platform
import psutil  # Bellek kullanımını izlemek için
from typing import List, Dict, Any, Set, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import requests
import sys
import subprocess
import gc  # For garbage collection

# Import configuration
sys.path.append('..')
import config

# Global WebDriver instance statistics - NOT the actual driver
global_driver = None
driver_creation_time = 0  # Track when the driver was created
searches_with_current_driver = 0  # Track how many searches have been done with the current driver
MAX_DRIVER_LIFETIME = config.WEBDRIVER_MAX_LIFETIME  # Maximum driver lifetime in seconds
MAX_SEARCHES_PER_DRIVER = config.WEBDRIVER_MAX_SEARCHES  # Recreate driver after this many searches to free memory

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
        print(f"Failed to get Chrome version: {e}")
    
    return None

def get_memory_usage():
    """
    Get current memory usage of the process in MB.
    
    Returns:
        float: Memory usage in MB
    """
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        # Convert to MB
        memory_mb = memory_info.rss / 1024 / 1024
        return memory_mb
    except:
        # Return -1 if can't get memory info
        return -1

def check_memory_limit():
    """
    Check if memory usage exceeds the limit and return whether driver should be restarted.
    
    Returns:
        bool: True if memory limit exceeded, False otherwise
    """
    try:
        memory_mb = get_memory_usage()
        memory_limit = config.WEBDRIVER_MEMORY_LIMIT
        
        if memory_mb > 0 and memory_mb > memory_limit:
            print(f"Memory usage ({memory_mb:.1f} MB) exceeds limit ({memory_limit} MB). Will recreate driver.")
            return True
        elif memory_mb > 0:
            print(f"Current memory usage: {memory_mb:.1f} MB (limit: {memory_limit} MB)")
            
        return False
    except:
        # Can't check memory, so don't force restart
        return False

def initialize_driver(force_new=False):
    """
    Initialize or return the global WebDriver instance.
    
    Args:
        force_new (bool): Force creation of a new driver
        
    Returns:
        WebDriver: The WebDriver instance
    """
    global global_driver, driver_creation_time, searches_with_current_driver
    
    current_time = time.time()
    
    # Check if memory limit exceeded
    memory_limit_exceeded = check_memory_limit()
    
    # Check if we need to create a new driver
    if (global_driver is None or 
        force_new or 
        memory_limit_exceeded or
        searches_with_current_driver >= MAX_SEARCHES_PER_DRIVER or
        (driver_creation_time > 0 and current_time - driver_creation_time > MAX_DRIVER_LIFETIME)):
        
        # If memory limit exceeded, log it
        if memory_limit_exceeded:
            print("Memory limit exceeded. Creating new driver to free memory.")
        
        # Close existing driver if it exists
        if global_driver is not None:
            try:
                global_driver.quit()
            except:
                pass
            global_driver = None
            
        # Force garbage collection to free memory
        gc.collect()
            
        # Configure Chrome settings
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run browser in invisible mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Memory-specific settings
        chrome_options.add_argument("--js-flags=--expose-gc")  # Expose garbage collector to JS
        chrome_options.add_argument("--single-process")  # Use single process
        chrome_options.add_argument("--disable-application-cache")  # Disable cache
        chrome_options.add_argument("--disable-infobars")  # Disable info bars
        chrome_options.add_argument("--disable-browser-side-navigation")  # Disable browser side navigation
        chrome_options.add_argument("--disable-features=TranslateUI")  # Disable translation
        chrome_options.add_argument("--disable-extensions")  # Disable extensions
        chrome_options.add_argument("--disable-component-extensions-with-background-pages")  # Disable extensions with background pages
        chrome_options.add_argument("--disable-default-apps")  # Disable default apps
        chrome_options.add_argument("--disable-breakpad")  # Disable crashpad/breakpad
        chrome_options.add_argument("--disable-dev-shm-usage")  # Disable shared memory usage
        chrome_options.add_argument("--disable-features=site-per-process")  # Disable site isolation
        
        # Set memory limits to reduce consumption
        chrome_options.add_argument("--memory-pressure-off")  # Disable memory pressure
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")  # Don't put backgrounded tabs into efficient mode
        
        # Search for Chrome in possible locations based on OS
        chrome_bin = None
        
        # Windows-specific paths
        if platform.system() == "Windows":
            possible_chrome_paths = [
                # Common Windows Chrome locations
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                # User directory Chrome installation
                os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe"),
                # Environment variables
                os.environ.get('CHROME_EXECUTABLE_PATH'),
            ]
            print(f"Searching for Chrome on Windows platform...")
        # Heroku/Linux paths
        else:
            possible_chrome_paths = [
                # For heroku-buildpack-chrome-for-testing
                '/app/.chrome/chrome/chrome',
                '/app/.apt/usr/bin/google-chrome',
                # For older buildpack
                '/app/.apt/opt/google/chrome/chrome',
                '/app/.heroku/google-chrome/bin/chrome',
                # For newer versions
                '/app/.chrome-for-testing/chrome-linux64/chrome',
                # Environment variables
                os.environ.get('GOOGLE_CHROME_BIN'),
                os.environ.get('GOOGLE_CHROME_SHIM'),
                # Default Linux paths
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                'chrome'
            ]
            print(f"Searching for Chrome on non-Windows platform...")
            
            # Additional search for Chrome in the filesystem on Linux/Heroku
            try:
                if os.path.exists('/app'):  # Check if we're on Heroku
                    chrome_paths_found = glob.glob('/app/**/*chrome*', recursive=True)
                    print(f"Found Chrome binaries on filesystem: {chrome_paths_found}")
                    possible_chrome_paths.extend(chrome_paths_found)
            except Exception as e:
                print(f"Error searching filesystem for Chrome: {e}")
        
        # Try each path
        for path in possible_chrome_paths:
            if path and os.path.exists(path) and os.access(path, os.X_OK):
                chrome_bin = path
                print(f"Found Chrome binary at: {chrome_bin}")
                break
        
        chrome_version = None
        if chrome_bin:
            # Set Chrome binary location if found
            chrome_options.binary_location = chrome_bin
            print(f"Setting chrome binary location to: {chrome_bin}")
            # Try to get Chrome version
            chrome_version = get_chrome_version(chrome_bin)
            if chrome_version:
                print(f"Detected Chrome version: {chrome_version}")
            else:
                # If version detection failed, just assume it's the same as Heroku chrome
                chrome_version = "135.0.7049.84"
                print(f"Failed to detect Chrome version, assuming: {chrome_version}")
        else:
            # If Chrome is not found in known locations, let webdriver_manager try to find it
            print("No Chrome binary found in expected locations. Will let WebDriver Manager handle it.")
        
        # Specify a unique user data directory
        temp_dir = os.path.join(tempfile.gettempdir(), f"chrome_temp_{os.getpid()}")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        # Additional settings
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--window-size=1280,720")  # Smaller window size to reduce memory
        
        # Page load and script timeout settings
        chrome_options.add_argument("--page-load-strategy=none")  # Don't wait for full page load
        
        try:
            # Start WebDriver using webdriver-manager
            print("Attempting to start Chrome with WebDriver...")
            
            try:
                # Try using selenium-wire instead of standard selenium for better compatibility
                from seleniumwire import webdriver as wire_webdriver
                
                # Try to use a specific ChromeDriver version that is compatible with Chrome 135
                # Instead of letting webdriver_manager auto-detect, we're forcing a compatible version
                # Using Chrome 134's driver as it's likely more compatible with Chrome 135
                driver_path = ChromeDriverManager(version="114.0.5735.90").install()
                service = Service(driver_path)
                
                # Try with selenium-wire first
                try:
                    print(f"Attempting to use seleniumwire with ChromeDriver 114.0.5735.90")
                    global_driver = wire_webdriver.Chrome(service=service, options=chrome_options)
                    print("Successfully created driver with seleniumwire!")
                except Exception as e:
                    print(f"Failed to create driver with seleniumwire: {e}")
                    # Fall back to regular selenium
                    print("Falling back to regular selenium")
                    global_driver = webdriver.Chrome(service=service, options=chrome_options)
                    
            except Exception as e:
                print(f"Failed to create driver with specified version: {e}")
                print("Trying one more approach with undetected-chromedriver...")
                
                try:
                    # Final fallback - try using undetected-chromedriver
                    import undetected_chromedriver as uc
                    global_driver = uc.Chrome(headless=True, options=chrome_options)
                    print("Successfully created driver with undetected-chromedriver!")
                except Exception as uc_e:
                    print(f"Failed with undetected-chromedriver: {uc_e}")
                    # Last resort - try regular Chrome
                    global_driver = webdriver.Chrome(options=chrome_options)
            
            print("Chrome WebDriver started successfully!")
            
            # Set timeouts
            global_driver.set_page_load_timeout(60)  # 60 seconds for page load timeout
            global_driver.set_script_timeout(60)     # 60 seconds for script timeout
            
            # Update creation time and search counter
            driver_creation_time = current_time
            searches_with_current_driver = 0
            
            # Clear the cache to minimize memory usage
            try:
                global_driver.execute_script("window.localStorage.clear();")
                global_driver.execute_script("window.sessionStorage.clear();")
                global_driver.execute_script("if(window.gc) window.gc();")  # Trigger JS garbage collection if available
            except:
                pass
            
        except Exception as e:
            print(f"Error creating WebDriver: {str(e)}")
            global_driver = None
            raise
    
    # Increment search counter
    searches_with_current_driver += 1
    
    # Return the global driver
    return global_driver

def get_youtube_videos(query: str, max_results: int = 15, timeout: int = None) -> List[Dict[str, Any]]:
    """
    Searches YouTube for a specific query, finds embeddable videos and sorts them by view count.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of videos to return
        timeout (int): Timeout in seconds for operations
        
    Returns:
        list: List of dictionaries containing video information
    """
    global global_driver
    
    # Use configuration default if not provided
    if timeout is None:
        timeout = config.WEBDRIVER_TIMEOUT
    
    # Try up to 3 times with a new driver if needed
    max_retries = 3
    for retry in range(max_retries):
        try:
            # Get or initialize the driver
            driver = initialize_driver(force_new=(retry > 0))
            
            if driver is None:
                print("Failed to initialize WebDriver, cannot search YouTube")
                return []
            
            # Go to YouTube search page and search for query (by relevance)
            try:
                print(f"Navigating to YouTube search page for: {query}")
                driver.get("https://www.youtube.com/results?search_query=" + query.replace(" ", "+"))
                
                # Wait for page to load with timeout
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "ytd-video-renderer"))
                )
            except TimeoutException:
                print(f"Timeout waiting for YouTube search results. Retry {retry+1}/{max_retries}")
                if retry == max_retries - 1:
                    # Last retry, return empty results
                    return []
                # Try with a new driver
                continue
            
            # Wait for page to load
            time.sleep(3)
            
            embeddable_videos = []
            processed_video_ids: Set[str] = set()  # Track processed video IDs
            scroll_count = 0
            min_scrolls = config.MIN_SCROLLS
            max_scrolls = config.MAX_SCROLLS
            
            # Maximum number of scrolls to limit memory usage
            max_scrolls = min(max_scrolls, 5)
            
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
                    
                    # Check different HTML structures (simplified approach to reduce parsing)
                    try:
                        # Just get all spans with text
                        all_spans = element.find_all('span')
                        for span in all_spans:
                            span_text = span.text.strip()
                            # Check for view count patterns
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
                    except Exception as e:
                        print(f"Error parsing view count: {e}")
                        # Continue with view count as 0
                    
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
                
                try:
                    # Scroll down to load more videos with timeout
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                    time.sleep(2)
                    scroll_count += 1
                    print(f"Page scrolled ({scroll_count}/{max_scrolls}), found {len(embeddable_videos)} embeddable videos so far.")
                except (TimeoutException, WebDriverException) as e:
                    print(f"Error scrolling page: {str(e)}")
                    # If we encounter an error while scrolling, but have some videos, return what we have
                    if embeddable_videos:
                        break
                    else:
                        # Try with a new driver
                        if retry < max_retries - 1:
                            raise
                
                # Check if we've scrolled the minimum number of times and found enough videos
                if scroll_count >= min_scrolls and len(embeddable_videos) >= max_results:
                    print(f"Exceeded minimum scroll count ({min_scrolls}) and found enough videos ({len(embeddable_videos)}). Stopping.")
                    break
                
                # Clear memory after each scroll
                try:
                    if 'soup' in locals():
                        del soup
                    if 'page_source' in locals():
                        del page_source
                    gc.collect()
                except:
                    pass
            
            # Sort results by view count
            embeddable_videos.sort(key=lambda x: x['view_count'], reverse=True)
            
            # Clean up BeautifulSoup objects and large variables to free memory
            try:
                if 'soup' in locals():
                    del soup
                if 'page_source' in locals():
                    del page_source
                if 'video_elements' in locals():
                    del video_elements
                gc.collect()
            except:
                pass
                
            # Return only the requested number of videos
            return embeddable_videos[:max_results]
        
        except Exception as e:
            print(f"Error during YouTube search: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Reset global driver on error
            if retry < max_retries - 1:
                print(f"Retrying with new driver ({retry+1}/{max_retries})")
                try:
                    if global_driver:
                        global_driver.quit()
                except:
                    pass
                global_driver = None
            else:
                print("Maximum retries exceeded, returning empty results")
                return []
    
    return []

def shutdown_driver():
    """
    Safely shutdown the global WebDriver instance.
    """
    global global_driver, searches_with_current_driver
    
    if global_driver is not None:
        try:
            # Clear cache before quitting
            try:
                global_driver.execute_script("window.localStorage.clear();")
                global_driver.execute_script("window.sessionStorage.clear();")
                global_driver.execute_script("if(window.gc) window.gc();")
            except:
                pass
                
            global_driver.quit()
        except:
            pass
        global_driver = None
        searches_with_current_driver = 0
        print("WebDriver shutdown successfully")
        
        # Force garbage collection
        gc.collect()

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