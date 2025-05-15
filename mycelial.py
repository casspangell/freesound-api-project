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
    import copy
    converted_model = copy.deepcopy(model)
    
    # Convert total duration if it's a string
    if isinstance(converted_model.get('total_duration'), str):
        converted_model['total_duration_seconds'] = time_to_seconds(converted_model['total_duration'])

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
        
        for old_key, new_key in time_key_mapping:
            # Try to convert from existing key
            if old_key in section:
                try:
                    section[new_key] = time_to_seconds(section[old_key])
                except Exception as e:
                    print(f"Warning: Could not convert {old_key} for section {section_name}: {e}")
        
        # Ensure all time keys exist with sensible defaults
        for key_base in ['start', 'end', 'midpoint', 'climax']:
            seconds_key = f"{key_base}_time_seconds"

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
        
        else:
            parts = user_input.split(" ", 1)
            keyword = parts[0]
            method = parts[1] if len(parts) > 1 else ""

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

            # # Queue sounds with enhanced context
            # score_manager.queue_sounds(keyword, cultural_context)
                
            continue


# Run the game
if __name__ == "__main__":
    text_input_game()