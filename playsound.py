import pygame
import os
import random
import time

def play_input_sound():
    # Generate a random sound file path
    input_sound_file = f"data/sound_files/input_sound/input_{random.randint(1, 4)}.mp3"
    print(f"\n🔊 Playing input sound: {input_sound_file}")
    
    # Check if the file exists and play it
    if os.path.exists(input_sound_file):
        pygame.mixer.init()
        input_sound = pygame.mixer.Sound(input_sound_file)
        input_channel = pygame.mixer.find_channel()
        if input_channel:
            print(f"Playing {input_sound_file}")
            input_channel.play(input_sound)
            # Wait for the sound to finish or for a shorter time if it's too long
            pygame.time.wait(min(int(input_sound.get_length() * 1000), 1500))
        else:
            print(f"⚠️ No available channel to play input sound")
    else:
        print(f"⚠️ Input sound file '{input_sound_file}' not found")


# Play the appropriate cultural shift sound
def play_cultural_shift_sound(shift_magnitude):
    
    # Determine level based on magnitude
    if shift_magnitude >= 0.2:
        shift_level = "high" 
        shift_sound_file = "data/sound_files/cultural_shift/shift.mp3"
    elif shift_magnitude >= 0.1:
        shift_level = "medium"
        shift_sound_file = "data/sound_files/cultural_shift/shift.mp3"  
    else:
        shift_level = "low"
        shift_sound_file = "data/sound_files/cultural_shift/shift.mp3"

    if os.path.exists(shift_sound_file):
        pygame.mixer.init()
        sound_file = "data/sound_files/cultural_shift/shift.mp3"
        shift_sound = pygame.mixer.Sound(sound_file)
        shift_channel = pygame.mixer.find_channel()

        if shift_channel:
            print(f"Playing {shift_sound}")
            shift_channel.play(shift_sound)
            # Wait for the sound to finish
            pygame.time.wait(min(int(shift_sound.get_length() * 1000), 3000))
        else:
            print(f"⚠️ No available channel to play {level} cultural shift sound")
    else:
        print(f"⚠️ Cultural shift sound file '{sound_file}' not found")