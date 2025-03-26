import pygame
import time
import os
import threading

# Reset and reinitialize pygame mixer to avoid conflicts
if pygame.mixer.get_init():
    pygame.mixer.quit()

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
pygame.mixer.set_num_channels(64)  # Use 64 channels to ensure plenty are available

print(f"Playsound module initialized with {pygame.mixer.get_num_channels()} audio channels")

# Cache for loaded sounds
sound_cache = {}

def play_sound(sound_file, block=False):
    """
    Play a sound file with robust error handling
    
    :param sound_file: Path to the sound file
    :param block: Whether to block until sound finishes playing
    """
    try:
        # Check if file exists
        if not os.path.exists(sound_file):
            print(f"⚠️ Sound file not found: {sound_file}")
            return False
        
        # Load from cache or create new Sound object
        if sound_file in sound_cache:
            sound = sound_cache[sound_file]
        else:
            sound = pygame.mixer.Sound(sound_file)
            sound_cache[sound_file] = sound
        
        # Find an available channel with retries
        channel = None
        retries = 0
        while channel is None and retries < 5:
            channel = pygame.mixer.find_channel()
            if channel is None:
                # If no channel is available, wait briefly and try again
                retries += 1
                print(f"⚠️ No available channel for playback, retrying ({retries}/5)...")
                # Stop oldest playing sound if we've reached max retries
                if retries >= 3:
                    for ch_num in range(pygame.mixer.get_num_channels()):
                        ch = pygame.mixer.Channel(ch_num)
                        if ch.get_busy():
                            print("⚠️ Stopping oldest sound to free a channel")
                            ch.stop()
                            break
                time.sleep(0.2)
                
                # Increase channels if needed
                if retries == 4 and pygame.mixer.get_num_channels() < 64:
                    new_channels = pygame.mixer.get_num_channels() * 2
                    print(f"⚠️ Increasing channels to {new_channels}")
                    pygame.mixer.set_num_channels(new_channels)
        
        if channel:
            # Play the sound
            channel.play(sound)
            print(f"🔊 Playing sound: {os.path.basename(sound_file)}")
            
            # Block if requested
            if block:
                # Get sound length in seconds
                duration = sound.get_length()
                time.sleep(duration)
            
            return True
        else:
            print("❗ Failed to find available channel after multiple retries")
            return False
            
    except Exception as e:
        print(f"❌ Error playing sound {sound_file}: {e}")
        return False

def play_in_thread(sound_file):
    """Play a sound in a separate thread"""
    threading.Thread(target=play_sound, args=(sound_file, True), daemon=True).start()

def play_input_sound():
    """Play the standard input sound"""
    input_sound_path = "data/sound_files/input_sound/input_2.mp3"
    
    # Check in multiple locations
    possible_paths = [
        input_sound_path,
        os.path.join(os.path.dirname(__file__), input_sound_path),
        "input_2.mp3"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            play_in_thread(path)
            return True
    
    print("⚠️ Input sound file not found in any expected location")
    return False

def play_cultural_shift_sound(magnitude):
    """Play a sound based on the magnitude of cultural shift"""
    shift_sound = "data/sound_files/cultural_shift/shift.mp3"
    
    # Check in multiple locations
    possible_paths = [
        shift_sound,
        os.path.join(os.path.dirname(__file__), shift_sound),
        os.path.basename(shift_sound)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            play_in_thread(path)
            return True
    
    print(f"⚠️ Cultural shift sound file not found: {shift_sound}")
    return False