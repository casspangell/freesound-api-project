def generate_drone_frequencies(notes_data=None, sound_files=None):
    """
    Generate frequencies for each voice in the drone choir
    
    Args:
        notes_data (dict, optional): Notes data for each voice (e.g., {'soprano': 'C#4'})
        sound_files (dict, optional): Sound file metadata to derive duration
    """
    import random
    from datetime import datetime
    
    # Default duration if no sound files provided
    default_duration_seconds = 60.0  # 1 minute default
    
    # Define frequency ranges for each voice type
    voice_ranges = {
        "soprano": {"min": 196.00, "max": 523.25},
        "alto": {"min": 164.81, "max": 392.00},
        "tenor": {"min": 130.81, "max": 349.23},
        "bass": {"min": 98.00, "max": 261.63}
    }
    
    # Note to frequency mapping (simplified)
    note_to_freq = {
        # Bass notes
        "C": 65.41, "C#": 69.30, "D": 73.42, "D#": 77.78, "E": 82.41, "F": 87.31,
        "F#": 92.50, "G": 98.00, "G#": 103.83, "A": 110.00, "A#": 116.54, "B": 123.47,
        
        # Tenor notes
        "C": 130.81, "C#": 138.59, "D": 146.83, "D#": 155.56, "E": 164.81, "F": 174.61,
        "F#": 185.00, "G": 196.00, "G#": 207.65, "A": 220.00, "A#": 233.08, "B": 246.94,
        
        # Alto notes
        "C": 261.63, "C#": 277.18, "D": 293.66, "D#": 311.13, "E": 329.63, "F": 349.23,
        "F#": 369.99, "G": 392.00, "G#": 415.30, "A": 440.00, "A#": 466.16, "B": 493.88,
        
        # Soprano notes
        "C": 523.25, "C#": 554.37, "D": 587.33, "D#": 622.25, "E": 659.26, "F": 698.46,
        "F#": 739.99, "G": 783.99, "G#": 830.61, "A": 880.00, "A#": 932.33, "B": 987.77
    }
    
    # Determine duration
    if sound_files:
        # If sound files are provided, try to get a representative duration
        durations = [file_data.get('duration_seconds', default_duration_seconds) 
                     for file_data in sound_files.values() 
                     if 'duration_seconds' in file_data]
        duration_seconds = sum(durations) / len(durations) if durations else default_duration_seconds
    else:
        duration_seconds = default_duration_seconds
    
    # Generate a frequency for each voice
    voices = []
    for voice_type in ["soprano", "alto", "tenor", "bass"]:
        # If we have note data for this voice, use it; otherwise generate random
        if notes_data and voice_type in notes_data and notes_data[voice_type]:
            note = notes_data[voice_type]
            # Try to find the frequency for the given note
            if note in note_to_freq:
                frequency = note_to_freq[note]
            else:
                # If note not found, generate a random frequency in the voice range
                range_data = voice_ranges[voice_type]
                frequency = random.uniform(range_data["min"], range_data["max"])
        else:
            # Generate random frequency in voice range
            range_data = voice_ranges[voice_type]
            frequency = random.uniform(range_data["min"], range_data["max"])
        
        # Create voice data
        voices.append({
            "frequency": frequency,
            "duration": duration_seconds,
            "voice_type": voice_type,
            "note": notes_data.get(voice_type, "") if notes_data else ""
        })
    
    return {
        "command": "update_drones",
        "timestamp": datetime.now().isoformat(),
        "voices": voices
    }