"""
Utility functions for time conversion in performance models.

This module provides helper functions to convert between time strings 
and seconds, and to transform performance models.
"""

def _format_time(seconds):
    """Format seconds as MM:SS"""
    if seconds is None:
        return "00:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
    
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
    Convert a performance model to ensure consistent seconds representation.
    
    Args:
        model (dict): Performance model 
    
    Returns:
        dict: Performance model with consistent seconds keys
    """
    # Create a deep copy to avoid modifying the original
    import copy
    converted_model = copy.deepcopy(model)
    
    # Mapping of existing keys to ensure consistency
    time_key_mapping = [
        ('start_seconds', 'start_time_seconds'),
        ('end_seconds', 'end_time_seconds'),
        ('midpoint_seconds', 'midpoint_time_seconds'),
        ('climax_seconds', 'climax_time_seconds')
    ]
    
    # Convert section times
    for section in converted_model.get('sections', []):
        for old_key, new_key in time_key_mapping:
            # If the old key exists, create the new key with the same value
            if old_key in section:
                section[new_key] = section[old_key]
            
            # Ensure the new key exists even if the old one doesn't
            if new_key not in section:
                section[new_key] = section.get(old_key, 0)
        
        # Debug print to verify keys
        print(f"Section {section.get('section_name', 'Unknown')}: {list(section.keys())}")
    
    return converted_model

    def _get_sound_duration(self, sound_file):
        """
        Get the duration of a sound file in seconds
        
        :param sound_file: Name of the sound file
        :return: Duration in seconds or default value of 30 seconds if unknown
        """
        # First check metadata from sound_files
        metadata = self.sound_files.get(sound_file, {})
        if 'duration_seconds' in metadata:
            return metadata.get('duration_seconds')
        
        # If not in metadata, try to get it from the sound object
        sound = self._load_sound(sound_file)
        if sound:
            try:
                return sound.get_length()
            except:
                pass
        
        # Default duration if we can't determine it
        print(f"⚠️ Could not determine duration for {sound_file}, using default (30s)")
        return 30.0

# Optional: If you want to include some basic testing
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
    # Additional manual tests
    print("Time Conversion Tests:")
    print(f"'01:30' to seconds: {time_to_seconds('01:30')}")
    print(f"90 seconds to time string: {seconds_to_time_str(90)}")