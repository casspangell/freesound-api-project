from api_client import WebAppClient, generate_drone_frequencies
import requests
import pygame
import time
import random
import os
import logging
import haiku
import movement
import threading
import json
from ashari import Ashari
from score import AshariScoreManager
from performance_clock import get_clock, start_clock, get_time_str, stop_clock
from playsound import play_sound, play_input_sound, play_cultural_shift_sound

# Initialize pygame (minimal initialization as playsound.py now handles the audio setup)
pygame.init()
print("Mycelial system initialized")

# Initialize Ashari
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

# Initialize the WebAppClient
webapp_client = WebAppClient()

# Initialize sound manager
score_manager = AshariScoreManager()

with open('data/sound_files.json', 'r') as f:
    sound_files = json.load(f)

# Clock callback to display time in console - FIXED VERSION
def clock_update(clock):
    """Callback that runs every second when the clock updates"""
    elapsed_seconds = clock.get_elapsed_seconds()
    
    # Only print a status update every 30 seconds
    if elapsed_seconds % 30 == 0:
        print(f"\n---\n🕒 Performance update - Time: {clock.get_time_str()} | Elapsed: {int(elapsed_seconds)} seconds\n---")

# Initialize the climax intensity system as part of the startup process
def initialize_systems():
    """Initialize all subsystems"""
    print("Initializing performance subsystems...")
    
    # Initialize the climax intensity system
    score_manager._initialize_climax_system()
    
    print("All subsystems initialized")
    
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

    # Main game loop
def text_input_game():
    # Initialize the global clock
    clock = get_clock()
    clock.add_callback(clock_update)
    
    print(f"\n🌿 Welcome to the Mycelial Memory Game! 🌿")
    print(f"Type 'begin' to start the experience...\n")
    
    # Wait for the user to type "begin"
    while True:
        user_input = input("Enter 'begin' to start: ").strip().lower()
        if user_input == "begin":
            # Start the performance clock
            start_clock()
            
            # Initialize the systems
            initialize_systems()
            
            # Start the playback
            score_manager.start_playback()
            
            print("Performance started! Type keywords to interact...")
            break
    
    while True:
        # Display current time with each prompt
        current_time = get_time_str()
        current_seconds = get_clock().get_elapsed_seconds()
        current_section = score_manager._get_current_section(current_seconds)
        section_name = current_section["section_name"] if current_section else "Unknown"
        
        print(f"\n[Time: {current_time} | Section: {section_name}] Type a keyword and method (e.g., 'wind haiku', 'fire move', 'rain score') or 'exit'.\n")
        
        user_input = input(f"\n[{current_time}] Enter a keyword and method: ").strip().lower()
        
        if user_input == "exit":
            print(f"Exiting game... 🌱")
            pygame.mixer.stop()  # Stop all sounds before exiting
            stop_clock()  # Stop the clock
            # Save Ashari's state before exiting
            ashari.save_state()
            os._exit(0)
            break
        
        if user_input == "ashari status":
            print(f"\n🧠 Ashari Cultural Memory Status:")
            for value, score in ashari.cultural_memory.items():
                print(f"  {value.capitalize()}: {score:.2f} ({ashari._describe_stance(score)})")
            continue

        if user_input == "server":
            print(f"\n📡 Sending frequencies to drone choir webapp...")
            
            # Get the current clip being played or select one
            current_clip = "1-5.mp3"  # Replace with actual current clip or selected clip
            
            # Get the notes for each voice from the sound file metadata
            if current_clip in sound_files:
                notes_data = {
                    "soprano": sound_files[current_clip].get("soprano", ""),
                    "alto": sound_files[current_clip].get("alto", ""),
                    "tenor": sound_files[current_clip].get("tenor", ""),
                    "bass": sound_files[current_clip].get("bass", ""),
                    "duration": sound_files[current_clip].get("duration_seconds", "")
                }
                print(f"Using notes from clip {current_clip}: {notes_data}")
            else:
                notes_data = None
                print(f"No note data found for clip {current_clip}, using random frequencies")
            
            # Get the data for the drone choir with the notes
            drone_data = generate_drone_frequencies(notes_data)
            
            # Send to Node.js server
            try:
                response = webapp_client.send_data("api/drone-update", drone_data)
                if response:
                    print(f"✅ Frequencies sent successfully! Response: {response['message']}")
                    
                    # Show the frequencies sent
                    for i, voice in enumerate(drone_data["voices"]):
                        voice_type = voice["voice_type"]
                        frequency = voice["frequency"]
                        duration = voice["duration"]
                        note = voice.get("note", "")
                        print(f"  {voice_type.capitalize()}: {frequency:.2f} Hz ({note}) for {duration}s")
                else:
                    print(f"❌ Failed to send frequencies to drone choir webapp.")
            except Exception as e:
                print(f"❌ Error sending frequencies: {str(e)}")
            
        if user_input == "time" or user_input == "clock":
            # Print detailed time and performance info
            elapsed_seconds = get_clock().get_elapsed_seconds()
            current_section = score_manager._get_current_section(elapsed_seconds)
            
            print(f"\n🕒 Performance Status:")
            print(f"  Time: {get_time_str()} ({int(elapsed_seconds)} seconds elapsed)")
            
            if current_section:
                # Calculate progress through section
                progress = score_manager._calculate_section_progress(elapsed_seconds, current_section)
                progress_percent = int(progress * 100)
                
                print(f"  Section: {current_section['section_name']} ({progress_percent}% complete)")
                
                # Display thematic context
                if "thematic_elements" in current_section:
                    themes = current_section["thematic_elements"]
                    if progress < 0.33 and "start" in themes:
                        print(f"  Current Theme: {themes['start']}")
                    elif progress < 0.66 and "midpoint" in themes:
                        print(f"  Current Theme: {themes['midpoint']}")
                    elif "end" in themes:
                        print(f"  Current Theme: {themes['end']}")
                    elif "climax" in themes:
                        print(f"  Current Theme: {themes['climax']}")
            else:
                print("  No active performance section")
                
            continue
            
        parts = user_input.split(" ", 1)
        keyword = parts[0]
        method = parts[1] if len(parts) > 1 else ""  # Default

        # Play a sound when there is an input
        play_input_sound()

        # Check for cultural shift
        cultural_shift = ashari.check_cultural_shift(keyword)

        if cultural_shift["significant_shift"]:
            shift_magnitude = cultural_shift["shift_magnitude"]
            shifted_value = cultural_shift["shifted_value"]
            # play_cultural_shift_sound(shift_magnitude)
        
        # Process the keyword through Ashari before performing other actions
        ashari_response = ashari.process_keyword(keyword)
        print(f"\n🧠 {ashari_response}")
        
        print(f"\nThe mycelium absorbs the concept of '{keyword}'... 🍄")
        if method == "haiku":
            haiku.generate_tts_haiku(keyword)
            play_input_sound()
        elif method == "move":
            print("🎶 The network whispers back with movement...")
            movement_result = movement.generate_movement_score(keyword)
            # Store the movement in Ashari's memory
            if keyword not in ashari.memory:
                ashari.memory[keyword] = {}
            ashari.memory[keyword]["movement"] = movement_result
            ashari.save_state()
            print(f"✅ Stored movement for '{keyword}': {movement_result}")
        elif method == "score":
            print(f"\n🎶 Generating sonic score for '{keyword}'...")
            
            # Get elapsed seconds for time-aware sound selection
            elapsed_seconds = get_clock().get_elapsed_seconds()
            current_section = score_manager._get_current_section(elapsed_seconds)
            section_progress = 0
            
            if current_section:
                section_progress = score_manager._calculate_section_progress(elapsed_seconds, current_section)
            
            # Get cultural context from Ashari
            cultural_context = {
                "overall_sentiment": ashari._calculate_overall_cultural_stance(),
                "key_values": [value for value, score in sorted(
                    ashari.cultural_memory.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:3]],
                "current_time": get_time_str(),
                "current_time_seconds": elapsed_seconds,
                "current_section": current_section["section_name"] if current_section else None,
                "section_progress": section_progress
            }
            
            play_input_sound()
            
            # Queue sounds with enhanced context
            score_manager.queue_sounds(keyword, cultural_context)

        elif method == "queue":
            # Print detailed information about the current playback queue
            with score_manager._playback_lock:
                queue = list(score_manager.playback_queue)
            
            print(f"\n🎶 Current Playback Queue:")
            if not queue:
                print("  Queue is empty.")
            else:
                for i, sound_file in enumerate(queue, 1):
                    # Get metadata for the sound file
                    metadata = score_manager.sound_files.get(sound_file, {})
                    section = metadata.get('section', 'unknown')
                    duration = metadata.get('duration_seconds', 0)
                    sentiment = metadata.get('sentiment_value', 0)
                    
                    # Format duration as MM:SS
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    duration_str = f"{minutes:02d}:{seconds:02d}"
                    
                    # Print detailed info about each queued sound
                    print(f"  {i}. {sound_file} (section: {section}, duration: {duration_str}, sentiment: {sentiment})")
                
                # Calculate total queue duration
                total_duration = sum(score_manager.sound_files.get(s, {}).get('duration_seconds', 0) for s in queue)
                total_minutes = int(total_duration // 60) 
                total_seconds = int(total_duration % 60)
                
                print(f"\n  Total queue duration: {total_minutes:02d}:{total_seconds:02d}")
            
            continue
        else:
            print(f"⚠️ Invalid method. Use 'haiku', 'move', or 'score'.")

# Run the game
if __name__ == "__main__":
    text_input_game()