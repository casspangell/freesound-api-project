import time
from performance_clock import get_clock

# This variable will be set by the mycelial.py module
# to provide a reference to the process_input function
_process_input_func = None

def set_process_function(func):
    """Set the function to process inputs during testing"""
    global _process_input_func
    _process_input_func = func

def test_at_time(minutes, seconds, keyword, method=None):
    """
    Test a keyword at a specific timestamp in the performance
    
    :param minutes: Minutes into the performance
    :param seconds: Seconds into the performance
    :param keyword: Keyword to process
    :param method: Method to apply (haiku, move, score)
    :return: None
    """
    # Calculate target time in seconds
    target_seconds = minutes * 60 + seconds
    
    # Get the clock
    clock = get_clock()
    
    # Store the actual time
    actual_seconds = clock.get_elapsed_seconds()
    actual_time_str = clock.get_time_str()
    
    # Temporarily override the clock's elapsed time
    print(f"\n🔍 TEST MODE: Simulating time {minutes:02d}:{seconds:02d} (actual time: {actual_time_str})")
    
    # Create a patch for the clock's get_elapsed_seconds method
    original_get_elapsed_seconds = clock.get_elapsed_seconds
    
    try:
        # Override the clock's get_elapsed_seconds method
        clock.get_elapsed_seconds = lambda: target_seconds
        
        # Format a combined input string if method is provided
        if method:
            test_input = f"{keyword} {method}"
        else:
            test_input = keyword
            
        # Process the test input
        if _process_input_func:
            _process_input_func(test_input)
        else:
            print("⚠️ Test processing function not set")
        
    finally:
        # Restore the original method
        clock.get_elapsed_seconds = original_get_elapsed_seconds
        print(f"🔍 TEST MODE ENDED: Returned to actual time {clock.get_time_str()}")

def time_string_to_seconds(time_str):
    """
    Convert a time string (MM:SS) to seconds
    
    :param time_str: Time string in format "MM:SS"
    :return: Total seconds
    """
    parts = time_str.split(":")
    if len(parts) == 2:
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        except ValueError:
            print(f"Invalid time format: {time_str}")
    
    print(f"Invalid time format: {time_str}. Use MM:SS format.")
    return 0