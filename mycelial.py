import requests
import pygame
import time
import random
import os
import logging
import haiku
import movement
import threading
from ashari import Ashari
from score import AshariScoreManager
from performance_clock import get_clock, start_clock, get_time_str, stop_clock
# Import the playsound module functions
from playsound import play_sound, play_input_sound, play_cultural_shift_sound

# Initialize pygame (minimal initialization as playsound.py now handles the audio setup)
pygame.init()
print("Mycelial system initialized")

# Initialize Ashari
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

# Initialize sound manager
score_manager = AshariScoreManager()

# Clock callback to display time in console
def clock_update(clock):
    """Callback that runs every second when the clock updates"""
    elapsed_seconds = clock.get_elapsed_seconds()
    
    # Get the current performance section
    current_section = score_manager._get_current_section(elapsed_seconds)
    
    # Every 30 seconds, print a status update (but only to the console, not interrupting interaction)
    if elapsed_seconds % 30 == 0 and current_section:
        progress = score_manager._calculate_section_progress(elapsed_seconds, current_section)
        progress_percent = int(progress * 100)
        print(f"\n---\n🕒 Performance update - Time: {clock.get_time_str()} | Section: {current_section['section_name']} ({progress_percent}%)\n---")

# Initialize the climax intensity system as part of the startup process
def initialize_systems():
    """Initialize all subsystems"""
    print("Initializing performance subsystems...")
    
    # Initialize the climax intensity system
    score_manager._initialize_climax_system()
    
    print("All subsystems initialized")
    
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
            score_manager.start_playback()
            # Initialize additional systems
            initialize_systems()
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
        else:
            print(f"⚠️ Invalid method. Use 'haiku', 'move', or 'score'.")

# Run the game
if __name__ == "__main__":
    text_input_game()