"""
Scheduler utility for running tasks on a schedule.
"""

import time
import json
from typing import Callable, List, Dict, Any
import schedule
import sys

# Import configuration
sys.path.append('..')
import config

def save_results_to_json(data: List[Dict[str, Any]], filename: str = "lecture_videos.json") -> None:
    """
    Saves results to a JSON file.
    
    Args:
        data (list): Data to save
        filename (str): Name of the file to save to
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Results saved to {filename}.")

def run_scheduled_job(job_function: Callable, schedule_time: str = None) -> None:
    """
    Runs a job on a schedule.
    
    Args:
        job_function (callable): Function to run
        schedule_time (str): Time to run the job (format: "HH:MM")
    """
    # Use configuration default if not provided
    if schedule_time is None:
        schedule_time = config.SCHEDULE_TIME
    
    # Schedule the job
    schedule.every().day.at(schedule_time).do(job_function)
    
    print(f"YouTube video search service started. {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Will run automatically every day at {schedule_time}.")
    
    # Check for first run
    if time.localtime().tm_hour == int(schedule_time.split(':')[0]) and time.localtime().tm_min == int(schedule_time.split(':')[1]):
        print("Matched start time, running immediately...")
        job_function()
    
    # Infinite loop to check scheduler
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("Program stopped by user.")
            break
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            # Wait 5 minutes and try again on error
            time.sleep(300) 