"""
Utility functions for time conversion in performance models.

This module provides helper functions to convert between time strings 
and seconds, and to transform performance models.
"""

def time_to_seconds(time_str):
    """
    Convert a time string in 'MM:SS' format to total seconds.
    
    Args:
        time_str (str): Time in 'MM:SS' format
    
    Returns:
        int: Total seconds
    
    Examples:
        >>> time_to_seconds('01:30')
        90
        >>> time_to_seconds('00:45')
        45
    """
    if not time_str or ':' not in time_str:
        return 0
    
    minutes, seconds = map(int, time_str.split(':'))
    return minutes * 60 + seconds

def seconds_to_time_str(total_seconds):
    """
    Convert total seconds to a 'MM:SS' time string.
    
    Args:
        total_seconds (int): Total number of seconds
    
    Returns:
        str: Formatted time string in 'MM:SS' format
    
    Examples:
        >>> seconds_to_time_str(90)
        '01:30'
        >>> seconds_to_time_str(45)
        '00:45'
    """
    minutes, seconds = divmod(int(total_seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def convert_model_to_seconds(model):
    """
    Convert a performance model with time strings to a seconds-based model.
    
    Ensures that all sections have *_seconds keys for start, end, midpoint, and climax.
    
    Args:
        model (dict): Performance model potentially containing time strings
    
    Returns:
        dict: Performance model with all times converted to seconds
    """
    # Create a deep copy to avoid modifying the original
    import copy
    converted_model = copy.deepcopy(model)
    
    # Convert total duration if it's a string
    if isinstance(converted_model.get('total_duration'), str):
        converted_model['total_duration_seconds'] = time_to_seconds(converted_model['total_duration'])
    
    # Default time mapping for sections if not specified
    default_section_times = {
        "Rising Action": {"start": 0, "end": 180, "midpoint": 60, "climax": 120},
        "Bridge": {"start": 180, "end": 240},
        "Falling Action": {"start": 240, "end": 360, "climax": 300}
    }
    
    # Mapping of old keys to new keys
    time_key_mapping = [
        ('start_time', 'start_time_seconds'),
        ('end_time', 'end_time_seconds'),
        ('midpoint_time', 'midpoint_time_seconds'),
        ('climax_time', 'climax_time_seconds')
    ]
    
    # Convert section times
    for section in converted_model.get('sections', []):
        section_name = section.get('section_name', '')
        default_times = default_section_times.get(section_name, {})
        
        for old_key, new_key in time_key_mapping:
            # Try to convert from existing key
            if old_key in section:
                try:
                    section[new_key] = time_to_seconds(section[old_key])
                except Exception as e:
                    print(f"Warning: Could not convert {old_key} for section {section_name}: {e}")
                    # Use default if conversion fails
                    section[new_key] = default_times.get(old_key.split('_')[0], 0)
            
            # If key doesn't exist, use default
            if new_key not in section:
                section[new_key] = default_times.get(new_key.split('_')[0], 0)
        
        # Ensure all time keys exist with sensible defaults
        for key_base in ['start', 'end', 'midpoint', 'climax']:
            seconds_key = f"{key_base}_time_seconds"
            if seconds_key not in section:
                section[seconds_key] = default_times.get(key_base, 0)
    
    return converted_model

# Optional: If you want to include some basic testing
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
    # Additional manual tests
    print("Time Conversion Tests:")
    print(f"'01:30' to seconds: {time_to_seconds('01:30')}")
    print(f"90 seconds to time string: {seconds_to_time_str(90)}")