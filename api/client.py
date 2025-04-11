"""
API client for handling authentication and API communication.
"""

import requests
import sys
import json
from typing import List, Dict, Any, Optional

# Import configuration
sys.path.append('..')
import config

def authenticate() -> Optional[str]:
    """
    Authenticates with the API and gets an access token.
    
    Returns:
        str: Authentication token or None on error
    """
    try:
        response = requests.post(config.API_URL_TO_AUTHENTICATE, json=config.API_USER)
        if response.status_code == 200:
            data = response.json()
            print(data.get('accessToken'))
            return data.get('accessToken')
        else:
            print(f"Authentication error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error during authentication: {str(e)}")
        return None

def get_courses_from_api() -> Optional[List[Dict[str, Any]]]:
    """
    Gets school, course, and lecture information from the API.
    
    Returns:
        list: List containing school, course, and lecture information or None on error
    """
    token = authenticate()
    if not token:
        print("Could not get token. Unable to retrieve schools and courses.")
        return None
    
    try:
        # Add headers similar to successful Postman request
        headers = {
            'x-access-token': token,
            'Cookie': f'accessToken={token}',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'User-Agent': 'PythonRequests'
        }
        
        print(f"Sending API request: {config.API_URL_TO_GET_COURSES}")
        print(f"Token: {token}")
        
        response = requests.get(config.API_URL_TO_GET_COURSES, headers=headers)
        
        print(f"API response: Status Code: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting schools and courses: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error during API request for schools and courses: {str(e)}")
        return None

def save_lecture_videos_to_api(lecture_videos: List[Dict[str, Any]]) -> bool:
    """
    Saves prepared lecture videos to the API.
    
    Args:
        lecture_videos (list): List of lecture videos to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    token = authenticate()
    if not token:
        print("Could not get token. Unable to save videos.")
        return False
    
    try:
        # Add headers similar to successful Postman request
        headers = {
            'x-access-token': token,
            'Cookie': f'accessToken={token}',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'User-Agent': 'PythonRequests'
        }
        
        print(f"Sending API request: {config.API_URL_TO_SAVE_LECTURE_VIDEOS}")
        print(f"Number of videos to save: {len(lecture_videos)}")
        
        response = requests.post(config.API_URL_TO_SAVE_LECTURE_VIDEOS, json=lecture_videos, headers=headers)
        
        print(f"API response: Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"API response: {response.json()}")
            return True
        else:
            print(f"Error saving videos: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error during API request to save videos: {str(e)}")
        return False 