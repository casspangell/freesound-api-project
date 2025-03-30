import json
import os
import threading
import time
from datetime import datetime
from openai import OpenAI
import config
import pygame
import logging
from performance_clock import get_clock, get_time_str
from time_utils import convert_model_to_seconds

class AshariScoreManager:
    def __init__(self, 
                 ashari=None,
                 repeat=False,
                 sound_files_path='data/sound_files.json', 
                 performance_model_path='data/performance_model.json',
                 base_sound_path='data/sound_files',
                 log_dir='logs'):
        """
        Initialize the Ashari Score Manager
        
        :param ashari: Ashari instance to use
        :param repeat: Whether to repeat sounds
        :param sound_files_path: Path to the JSON file containing sound file metadata
        :param performance_model_path: Path to the JSON file containing performance timeline
        :param base_sound_path: Base directory for sound files
        :param log_dir: Directory to store GPT interaction logs
        """

        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )

        # Unload pygame mixer if already initialized to reset it
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        
        # Initialize pygame mixer with more channels
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.set_num_channels(64)  # Use 64 channels to ensure enough are available

        # Playback queue with persistent memory
        self.playback_queue = ["intro.mp3"]
        self._current_sounds = []
        self._current_sound = None
        self.repeat = repeat

        # Create Ashari instance if not provided
        if ashari is None:
            from ashari import Ashari
            ashari = Ashari()
            ashari.load_state()
        
        # Store the Ashari instance
        self.ashari = ashari

        # Initialize OpenAI client
        self.client = OpenAI(api_key=config.CHAT_API_KEY)
        
        # Ensure log directory exists
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Load sound files metadata
        self.sound_files = {}
        self._load_sound_files(sound_files_path)
        
        # Load performance model
        self.performance_model = {}
        self._load_performance_model(performance_model_path)
        
        # Base sound path
        self.base_sound_path = base_sound_path
        
        # Sound playback queue
        self.sound_queue = []
        
        # Cached sound objects
        self._sound_cache = {}
        
        # Cached section info
        self._current_section = None
        self._last_section_check_time = 0
        
        # Continuous playback management
        self._current_sound = None
        self._playback_lock = threading.Lock()
        self._playback_thread = None
        self._stop_event = threading.Event()
        
        print(f"🎵 Ashari Score Manager initialized with {len(self.sound_files)} sound files")

    def _initialize_climax_system(self):
        """Initialize the climax intensity system"""
        try:
            # Import the ClimaxIntensitySystem class
            from climax_system import ClimaxIntensitySystem
            
            # Create an instance with reference to this score manager
            self.climax_system = ClimaxIntensitySystem(self)
            
            # Start the monitoring
            self.climax_system.start_monitoring()
            
            print("✅ Climax intensity system initialized")
            return True
        except Exception as e:
            print(f"❌ Error initializing climax system: {e}")
            return False

    def _load_sound_files(self, sound_files_path):
        """Load sound files from JSON, with robust error handling"""
        # Possible paths for sound files JSON
        possible_paths = [
            sound_files_path,
            os.path.join(os.path.dirname(__file__), sound_files_path),
            os.path.join(os.path.dirname(__file__), 'data/sound_files.json'),
            '/data/sound_files.json',
            'sound_files.json'
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self.sound_files = json.load(f)
                        print(f"✅ Loaded sound files from {path}")
                        return
            except Exception as e:
                print(f"❌ Error trying to load sound files from {path}: {e}")
        
        print("❌ ERROR: Could not find sound_files.json")
    
    def _load_performance_model(self, performance_model_path):
        """Load performance model from JSON"""
        try:
            with open(performance_model_path, 'r', encoding='utf-8') as f:
                original_model = json.load(f)
            
            # Convert the model to use seconds consistently
            self.performance_model = convert_model_to_seconds(original_model)
            
            print(f"✅ Loaded performance model from {performance_model_path}")
            return True
        except Exception as e:
            print(f"❌ Error loading performance model: {e}")
            return False

    def _load_sound(self, filename: str) -> pygame.mixer.Sound:
        """Load a sound file with the correct section-based path"""
        if filename is None:
            print("⚠️ Cannot load sound: filename is None")
            return None
        
        if filename in self._sound_cache:
            return self._sound_cache[filename]
        
        # Determine which folder to look in based on filename prefix
        section_folder = None
        if filename.startswith("1-"):
            section_folder = "Rising Action"
        elif filename.startswith("2-"):
            section_folder = "middle"
        elif filename.startswith("3-"):
            section_folder = "climactic" 
        elif filename.startswith("bridge-"):
            section_folder = "Bridge"
        elif filename == "end_transition.mp3":
            section_folder = "End"
        else:
            # Find the section from metadata if available
            section_folder = next(
                (metadata['section'] for file, metadata in self.sound_files.items() if file == filename), 
                'narrative'  # default section if not found
            )
        
        # Try multiple possible paths based on your actual directory structure
        possible_paths = [
            # Main paths based on your directory structure
            os.path.join("data", "sound_files", section_folder, filename),
            os.path.join("data/sound_files", section_folder, filename),
            
            # Try mapped section names
            os.path.join("data", "sound_files", "Intro", filename),
            os.path.join("data", "sound_files", "Rising Action", filename),
            os.path.join("data", "sound_files", "middle", filename),
            os.path.join("data", "sound_files", "climactic", filename),
            os.path.join("data", "sound_files", "Bridge", filename),
            os.path.join("data", "sound_files", "End", filename),
            
            # Try with different base paths
            os.path.join(self.base_sound_path, section_folder, filename),
            
            # Direct paths
            os.path.join(section_folder, filename),
            filename
        ]
        
        # Filter out None values
        possible_paths = [path for path in possible_paths if path]
        
        # Print debug info for file loading
        print(f"🔍 Looking for sound: {filename} (section: {section_folder})")
        
        for full_path in possible_paths:
            try:
                if os.path.exists(full_path):
                    print(f"✅ Found sound at: {full_path}")
                    sound = pygame.mixer.Sound(full_path)
                    
                    # Cache the sound
                    self._sound_cache[filename] = sound
                    return sound
            except Exception as e:
                pass  # Try next path
        
        # If we got here, we couldn't find the file
        print(f"⚠️ Sound file not found in any expected location: {filename}")
        print(f"   Tried paths: {', '.join(possible_paths)}")
        return None


    def _continuous_playback(self):
        """Continuously play sounds in the playback queue with section-aware repeats and smooth crossfades"""
        import haiku
        
        # Reserve specific channels for main queue playback - avoid conflicts with climax system
        RESERVED_CHANNELS = 16  # Reserve 16 of the 64 channels for main queue
        main_channels = [pygame.mixer.Channel(i) for i in range(RESERVED_CHANNELS)]
        current_channel_index = 0
        next_channel_index = 1  # For crossfading
        
        # Crossfade settings
        CROSSFADE_START = 5.0  # Start crossfade 5 seconds before end
        FADE_DURATION = 5.0    # Duration of fades in seconds
        
        # Active channel tracking for crossfading
        current_channel = None
        next_channel = None
        current_sound_file = None
        current_sound_end_time = 0
        crossfade_started = False
        end_transition_added = False
        
        while not self._stop_event.is_set():
            try:
                current_time = time.time()

                if not end_transition_added:
                    # Get performance time
                    from performance_clock import get_clock
                    performance_time = get_clock().get_elapsed_seconds()
                    
                    # Get current section
                    current_section = self._get_current_section(performance_time)

                    # if current_section and current_section["section_name"] == "Bridge":
                    #     print("+++BRIDGE SECTION")

                    # if current_section and current_section["section_name"] == "Rising Action":
                    #     print("+++RISING ACTION")

                    # if current_section and current_section["section_name"] == "Falling Action":
                    #     print("+++FALLING ACTION")
                    
                    # If we're in the End section, immediately play end_transition.mp3
                    if current_section and current_section["section_name"] == "End":
                        print("🏁 End section reached - immediately playing end_transition.mp3")
                        
                        # Clear the queue and add end_transition.mp3
                        with self._playback_lock:
                            self.playback_queue.clear()
                            self.playback_queue.insert(0, "end_transition.mp3")
                            end_transition_added = True
                            
                            # If a sound is currently playing, stop it
                            if current_channel and current_channel.get_busy():
                                print("🔇 Stopping current sound to start end transition")
                                current_channel.stop()
                                
                                # Reset current sound tracking variables
                                current_channel = None
                                current_sound_file = None
                                crossfade_started = False
                
                # CASE 1: No active sound playing, start a new one
                if current_channel is None or not current_channel.get_busy():
                    crossfade_started = False
                    
                    # Check if playback queue is empty
                    if not self.playback_queue:
                        # If we have a current sound, add it back to the queue
                        if current_sound_file and current_sound_file != "None":
                            print(f"Queue empty, adding current sound back: {current_sound_file}")
                            with self._playback_lock:
                                self.playback_queue.append(current_sound_file)
                        # If no current sound is available, add a default based on current section
                        else:
                            # Get current time from performance clock
                            from performance_clock import get_clock
                            current_time_seconds = get_clock().get_elapsed_seconds()
                            current_section = self._get_current_section(current_time_seconds)
                            
                            # If we have a valid section, get an appropriate sound for it
                            if current_section:
                                section_name = current_section["section_name"]
                                section_sounds = [
                                    filename for filename, metadata in self.sound_files.items()
                                    if metadata.get('section', '') == section_name
                                ]
                                
                                if section_sounds:
                                    import random
                                    default_sound = random.choice(section_sounds)
                                    print(f"Queue empty, no current sound, adding default for section {section_name}: {default_sound}")
                                    with self._playback_lock:
                                        self.playback_queue.append(default_sound)
                                else:
                                    # Last resort - just pick any sound
                                    all_sounds = list(self.sound_files.keys())
                                    if all_sounds:
                                        default_sound = all_sounds[0]
                                        print(f"Queue empty, no section sounds, adding fallback: {default_sound}")
                                        with self._playback_lock:
                                            self.playback_queue.append(default_sound)
                    
                    # Get the next sound file from queue
                    with self._playback_lock:
                        if not self.playback_queue:
                            time.sleep(0.1)
                            continue
                        sound_file = self.playback_queue.pop(0)
                        
                        # Verify sound_file is not None - safety check
                        if sound_file is None or sound_file == "None":
                            print("⚠️ WARNING: Found 'None' in playback queue, skipping")
                            continue
                    
                    # Store current sound being played
                    current_sound_file = sound_file
                    self._current_sound = sound_file
                    
                    # Load the sound
                    sound = self._load_sound(sound_file)
                    
                    if sound:
                        # Get metadata for logging
                        metadata = self.sound_files.get(sound_file, {})
                        duration = metadata.get('duration_seconds', 30)
                        
                        logging.info(f"Playing sound: {sound_file} (duration: {duration:.1f}s)")
                        
                        # Setup channel for new sound
                        current_channel = main_channels[current_channel_index]
                        current_channel_index = (current_channel_index + 1) % RESERVED_CHANNELS
                        
                        # Update next channel index too
                        next_channel_index = (current_channel_index + 1) % RESERVED_CHANNELS
                        
                        # If channel is busy, stop it to make room for new sound
                        if current_channel.get_busy():
                            current_channel.stop()
                        
                        # Start with full volume if no crossfade in progress
                        current_channel.set_volume(0.8)
                        current_channel.play(sound)
                        
                        # Calculate when this sound will end
                        current_sound_end_time = current_time + duration
                        
                        # Print remaining playback queue
                        with self._playback_lock:
                            if self.playback_queue:
                                print("\n🎶 Remaining Playback Queue:")
                                for i, remaining_sound in enumerate(self.playback_queue, 1):
                                    print(f"  {i}. {remaining_sound}")
                            else:
                                print("  Queue is now empty.")
                
                # CASE 2: Sound is playing, check if we need to prepare for crossfade
                elif current_channel and current_channel.get_busy() and not crossfade_started:
                    # Check if we're within CROSSFADE_START seconds of the end
                    time_remaining = current_sound_end_time - current_time
                    
                    if time_remaining <= CROSSFADE_START:
                        # We need to prepare the next sound
                        crossfade_started = True
                        
                        # Check if there's anything in the queue, if not add current sound back
                        with self._playback_lock:
                            if not self.playback_queue:
                                # Check if repeating this sound would cross a section boundary
                                if self._would_cross_section_boundary(current_sound_file, time_remaining + CROSSFADE_START):
                                    # Select a sound appropriate for the next section
                                    next_section_sound = self._select_sound_for_next_section(current_sound_file)
                                    if next_section_sound and next_section_sound != "None":
                                        print(f"⚠️ Section boundary detected! Using {next_section_sound} from new section for crossfade")
                                        self.playback_queue.insert(0, next_section_sound)
                                    else:
                                        # Fallback if next_section_sound is None or "None"
                                        print(f"⚠️ Section boundary detected but got invalid next section sound, reusing current for crossfade: {current_sound_file}")
                                        self.playback_queue.insert(0, current_sound_file)
                                else:
                                    # Current sound's section is still valid, repeat it
                                    print(f"Preparing for crossfade, adding {current_sound_file} back to queue (queue was empty)")
                                    self.playback_queue.insert(0, current_sound_file)
                        
                        # Now get the next sound from the queue (which we just ensured has something)
                        with self._playback_lock:
                            next_sound_file = self.playback_queue[0]  # Peek but don't remove yet
                        
                        # Load the next sound
                        next_sound = self._load_sound(next_sound_file)
                        
                        if next_sound:
                            # Setup channel for the next sound
                            next_channel = main_channels[next_channel_index]
                            
                            # If next channel is busy, stop it
                            if next_channel.get_busy():
                                next_channel.stop()
                            
                            # Start with zero volume (will fade in)
                            next_channel.set_volume(0.0)
                            
                            # Calculate current fade progress and apply to both channels
                            start_fade_in = time.time()  # When we started the fade
                            
                            # Start playing the next sound (it starts silent)
                            next_channel.play(next_sound)
                            
                            # Begin the crossfade process - fade out current, fade in next
                            fade_complete = False
                            while not fade_complete and not self._stop_event.is_set():
                                now = time.time()
                                fade_progress = min(1.0, (now - start_fade_in) / FADE_DURATION)
                                
                                # Apply fade out to current channel (from 0.8 to 0)
                                current_vol = max(0.0, 0.8 * (1.0 - fade_progress))
                                current_channel.set_volume(current_vol)
                                
                                # Apply fade in to next channel (from 0 to 0.8)
                                next_vol = min(0.8, 0.8 * fade_progress)
                                next_channel.set_volume(next_vol)
                                
                                # Check if fade is complete
                                if fade_progress >= 1.0:
                                    fade_complete = True
                                    # The next sound is now our current sound
                                    current_channel = next_channel
                                    current_sound_file = next_sound_file
                                    
                                    # Pop the sound we just started playing from the queue
                                    with self._playback_lock:
                                        if self.playback_queue and self.playback_queue[0] == next_sound_file:
                                            self.playback_queue.pop(0)
                                    
                                    # Update tracking variables for the new current sound
                                    metadata = self.sound_files.get(current_sound_file, {})
                                    duration = metadata.get('duration_seconds', 30)
                                    current_sound_end_time = now + duration
                                    
                                    # Set next channel index for future crossfades
                                    current_channel_index = next_channel_index
                                    next_channel_index = (current_channel_index + 1) % RESERVED_CHANNELS
                                    
                                    # Reset crossfade flag
                                    crossfade_started = False
                                    
                                    print(f"✨ Crossfade complete - Now playing: {current_sound_file}")
                                    
                                    # Break out of the fade loop
                                    break
                                
                                # Small sleep to avoid CPU spinning
                                time.sleep(0.05)
                
                # Sleep to avoid consuming too much CPU in main loop
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in continuous playback: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1.0)  # Sleep longer on error

    def _would_cross_section_boundary(self, sound_file, duration):
        """
        Check if repeating this sound would cross a section boundary
        
        :param sound_file: The sound file to check
        :param duration: Duration of the sound in seconds
        :return: True if playing this sound would cross a section boundary
        """
        # Get current time from performance clock
        from performance_clock import get_clock
        current_time = get_clock().get_elapsed_seconds()
        
        # Get the current section
        current_section = self._get_current_section(current_time)
        
        # Calculate where we'll be after this sound plays again
        future_time = current_time + duration
        
        # Get the section we'd be in at that future time
        future_section = self._get_current_section(future_time)
        
        # Special case for end_transition.mp3 - never consider it a section boundary
        if sound_file == "end_transition.mp3":
            print(f"🏁 End transition is playing - ignoring section boundary checks")
            return False
        
        # Special check for transition to End section
        if future_section and future_section["section_name"] == "End" and current_section and current_section["section_name"] != "End":
            print(f"🏁 End section boundary detected! Current={current_section['section_name']}, Future=End")
            print(f"Current time: {int(current_time//60):02d}:{int(current_time%60):02d}, Future time: {int(future_time//60):02d}:{int(future_time%60):02d}")
            return True
        
        # Check if we'd cross a section boundary
        if current_section and future_section and current_section["section_name"] != future_section["section_name"]:
            print(f"Section boundary detected: {current_section['section_name']} -> {future_section['section_name']}")
            print(f"Current time: {int(current_time//60):02d}:{int(current_time%60):02d}, Future time: {int(future_time//60):02d}:{int(future_time%60):02d}")
            return True
        
        # Also check if the sound file's section doesn't match the future section
        sound_metadata = self.sound_files.get(sound_file, {})
        sound_section = sound_metadata.get('section', '')
        
        if future_section:
            future_sound_section = future_section["section_name"]
            if sound_section and sound_section != future_sound_section:
                print(f"Sound section mismatch: {sound_section} vs {future_sound_section}")
                return True
        
        return False

    def _select_sound_for_next_section(self, current_sound):
        """
        Select an appropriate sound for the next section
        
        :param current_sound: The current sound that would cross the boundary
        :return: A new sound file appropriate for the next section
        """
        # Get current time from performance clock
        from performance_clock import get_clock
        current_time = get_clock().get_elapsed_seconds()
        
        # Calculate where we'll be after this sound plays again
        sound_metadata = self.sound_files.get(current_sound, {})
        duration = sound_metadata.get('duration_seconds', 30)  # Default to 30s if unknown
        future_time = current_time + duration
        
        # Get the section we'd be in at that future time
        future_section = self._get_current_section(future_time)
        
        if not future_section:
            print("⚠️ Couldn't determine future section, using default sound")
            return list(self.sound_files.keys())[0] if self.sound_files else current_sound  # Use first sound or current as fallback
        
        # Map the performance section to sound section
        target_section = future_section["section_name"]
        
        # Special handling for End section - use end_transition.mp3
        if target_section == "End":
            print("🏁 Detected transition to End section - playing end_transition.mp3")
            return "end_transition.mp3"
        
        # Special handling for Falling Action section - use falling voice clips if appropriate
        if target_section == "Falling Action":
            # Check if we should use the special falling clips
            falling_clips_available = False
            for i in range(1, 5):
                path = os.path.join("data", "sound_files", "Falling Voices", f"falling_{i}.mp3")
                if os.path.exists(path):
                    falling_clips_available = True
                    break
                    
            if falling_clips_available:
                import random
                falling_clip = f"falling_{random.randint(1, 4)}.mp3"
                print(f"🍂 Selected Falling Action clip: {falling_clip}")
                return falling_clip
        
        # Find all sounds from the target section
        section_sounds = [
            filename for filename, metadata in self.sound_files.items()
            if metadata.get('section', '') == target_section
        ]
        
        if not section_sounds:
            print(f"⚠️ No sounds found for section {target_section}, using current sound as fallback")
            return current_sound  # Use current sound as fallback instead of a random one
        
        # Select a random sound from the appropriate section
        import random
        selected_sound = random.choice(section_sounds)
        
        print(f"Selected sound {selected_sound} for next section {target_section}")
        return selected_sound


    def start_playback(self):
        """Start continuous playback thread if not already running"""
        # Ensure only one playback thread is running
        if self._playback_thread and self._playback_thread.is_alive():
            return
        
        # Reset stop flag
        self._stop_event.clear()  # Changed from self._stop_playback.clear()
        
        # Start playback thread
        self._playback_thread = threading.Thread(target=self._continuous_playback)
        self._playback_thread.daemon = True
        self._playback_thread.start()
        print("🎵 Score playback system started")
    

    def _get_current_section(self, current_time_seconds: float):
        """Get the current section based on elapsed time"""
        # Use cached value if checked recently (within 5 seconds)
        if self._current_section and time.time() - self._last_section_check_time < 5:
            return self._current_section
        
        # Check if performance_model has sections
        if not self.performance_model or "sections" not in self.performance_model:
            print("⚠️ No performance model sections available")
            return None
        
        # Find the section containing the current time
        for section in self.performance_model["sections"]:
            if (section["start_time_seconds"] <= current_time_seconds and
                    section["end_time_seconds"] >= current_time_seconds):
                self._current_section = section
                self._last_section_check_time = time.time()
                return section
        
        # If we're past the end of the defined sections, return the last one
        if current_time_seconds > self.performance_model["sections"][-1]["end_time_seconds"]:
            self._current_section = self.performance_model["sections"][-1]
            self._last_section_check_time = time.time()
            return self._current_section
        
        # If we're before the first section, return the first one
        if current_time_seconds < self.performance_model["sections"][0]["start_time_seconds"]:
            self._current_section = self.performance_model["sections"][0]
            self._last_section_check_time = time.time()
            return self._current_section
        
        # If we reach here, something unexpected happened
        print(f"⚠️ Could not determine section for time {current_time_seconds}")
        return None

    def _get_current_theme(self, section, progress):
        """Get the appropriate theme based on section progress"""
        if not section or "thematic_elements" not in section:
            return None
            
        themes = section["thematic_elements"]
        
        # For Rising Action, consider midpoint and climax timing if available
        if section["section_name"] == "Rising Action" and "midpoint_time_seconds" in section and "climax_time_seconds" in section:
            section_start = section["start_time_seconds"]
            section_end = section["end_time_seconds"]
            midpoint_time = section["midpoint_time_seconds"]
            climax_time = section["climax_time_seconds"]
            
            current_time = section_start + (section_end - section_start) * progress
            
            if current_time < midpoint_time:
                return themes.get("start")
            elif current_time < climax_time:
                return themes.get("midpoint")
            else:
                return themes.get("climax")
        else:
            # For other sections, use simple progress thresholds
            if progress < 0.33:
                return themes.get("start")
            elif progress < 0.66:
                return themes.get("midpoint")
            else:
                return themes.get("end", themes.get("climax"))
    
    def _calculate_section_progress(self, current_time_seconds: float, section):
        """Calculate progress through the current section (0.0 to 1.0)"""
        section_start = section["start_time_seconds"]
        section_end = section["end_time_seconds"]
        section_duration = section_end - section_start
        
        if section_duration <= 0:
            return 0.0
        
        progress = (current_time_seconds - section_start) / section_duration
        return max(0.0, min(1.0, progress))  # Clamp between 0 and 1
    
    # def _map_performance_section_to_sound_section(self, performance_section: str) -> str:
    #     """Map performance section names to sound file section categories"""
    #     section_mapping = {
    #         "Rising Action": "intro",
    #         "Bridge": "middle",
    #         "Falling Action": "climactic"
    #     }
        
    #     return section_mapping.get(performance_section, "middle")

    def select_sound_with_gpt(self, word: str, cultural_context: dict = None) -> str:
        """
        Select a sound using GPT, enhanced with performance timeline awareness and current queue awareness
        
        :param word: Input keyword
        :param cultural_context: Context including performance time and cultural data
        :return: Selected sound filename or None
        """
        if cultural_context is None:
            cultural_context = {}
        
        # Get performance context
        current_time_seconds = get_clock().get_elapsed_seconds()
        current_section = self._get_current_section(current_time_seconds)
        
        # Enhance cultural context with performance data
        performance_context = {
            "performance_time": get_time_str(),
            "performance_time_seconds": current_time_seconds
        }
        
        if current_section:
            section_progress = self._calculate_section_progress(current_time_seconds, current_section)
            section_name = current_section["section_name"]
            
            performance_context.update({
                "current_section": section_name,
                "section_progress": section_progress
            })
            
            # Add thematic elements based on progress
            current_theme = self._get_current_theme(current_section, section_progress)
            if current_theme:
                performance_context["current_theme"] = current_theme
            
            # Filter sounds for appropriate section
            sound_section = section_name
            
            # Add to performance context
            performance_context["mapped_sound_section"] = sound_section
        
        # Merge with existing cultural context
        cultural_context.update(performance_context)
        
        # Prepare a comprehensive context
        cultural_details = {
            "overall_sentiment": cultural_context.get('overall_sentiment', 0),
            "current_cultural_memory": {
                value: score for value, score in self.ashari.cultural_memory.items()
            },
            "strongest_values": [
                {"value": value, "score": score} 
                for value, score in sorted(
                    self.ashari.cultural_memory.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:3]
            ],
            "performance_context": performance_context
        }
        
        # Get current queue for context
        with self._playback_lock:
            current_queue = list(self.playback_queue)
        
        # Construct the system prompt
        system_prompt = """
            You are the Sound Selector for the Ashari cultural narrative. Your task is to choose the most thematically and emotionally appropriate sound file based on the given keyword and cultural context.

            REQUIREMENTS:
            1. ALWAYS return a VALID FILENAME from the available sound files.
            2. Use the dialogue section as the primary method of selection.
            3. Consider both the current cultural memory and the performance timeline position.
            4. Match the sound file's dialogue to the input word's emotional and cultural resonance.
            5. Select sounds that align with the current section of the performance.
            6. DO NOT select any sound that is already in the current playback queue.

            Selection Criteria:
            - IMPORTANT: Avoid selecting any sound file that is currently in the queue
            - If a specific sound section is provided (intro, middle, climactic), STRONGLY prefer sounds from that section
            - Analyze how each sound file's dialogue connects to:
              a) The input keyword
              b) The current cultural sentiment
              c) The strongest cultural values
              d) The current performance theme
            - Prioritize dialogues that:
              - Reflect the emotional nuance of the keyword
              - Align with the Ashari's current cultural stance
              - Match the current performance section's thematic elements
              - Provide depth and context to the cultural experience

            Evaluation Process:
            1. Read each dialogue carefully
            2. Compare the dialogue's themes to the keyword and cultural context
            3. Consider the sentiment value as a secondary factor
            4. Select the file that most profoundly captures the moment's emotional and cultural significance
               within the current performance context

            OUTPUT FORMAT:
            - Respond ONLY with the EXACT filename of the chosen sound file
            - NO additional explanation or text
            - If no perfect match exists, choose the closest thematic representation
            """

        # Filter sounds based on performance section if applicable
        filtered_sound_files = self.sound_files
        if "mapped_sound_section" in performance_context:
            target_section = performance_context["mapped_sound_section"]
            filtered_sound_files = {
                filename: metadata 
                for filename, metadata in self.sound_files.items()
                if metadata.get('section') == target_section
            }
            
            # If no sounds in the preferred section, use all sounds
            if not filtered_sound_files:
                filtered_sound_files = self.sound_files
                print(f"⚠️ No sounds found in section '{target_section}', using all sounds")
        
        # Further filter to remove sounds that are already in the queue
        filtered_sound_files = {
            filename: metadata 
            for filename, metadata in filtered_sound_files.items()
            if filename not in current_queue
        }
        
        # If all appropriate sounds are in the queue, revert to original filtered list
        if not filtered_sound_files:
            print("⚠️ All sounds from the appropriate section are already in the queue.")
            filtered_sound_files = {
                filename: metadata 
                for filename, metadata in self.sound_files.items()
                if filename not in current_queue
            }
            
            # If absolutely all sounds are in the queue, use the full list as a last resort
            if not filtered_sound_files:
                print("⚠️ All sounds are currently in the queue. Using full sound library.")
                filtered_sound_files = self.sound_files

        user_prompt = f"""
            Select a sound file for the keyword: '{word}'

            CULTURAL CONTEXT:
            - Overall Sentiment: {cultural_context.get('overall_sentiment', 'N/A')}
            - Key Cultural Values: {cultural_context.get('key_values', 'N/A')}

            PERFORMANCE CONTEXT:
            - Current Time: {cultural_context.get('performance_time', 'N/A')}
            - Current Section: {cultural_context.get('current_section', 'N/A')}
            - Section Progress: {cultural_context.get('section_progress', 'N/A')}
            - Current Theme: {cultural_context.get('current_theme', 'N/A')}
            - Preferred Sound Section: {cultural_context.get('mapped_sound_section', 'N/A')}

            CURRENT PLAYBACK QUEUE:
            {json.dumps(current_queue, indent=2)}
            IMPORTANT: Do NOT select any sound file that is already in this queue.

            AVAILABLE SOUND FILES:
            {json.dumps([
                {
                    "filename": filename, 
                    "sentiment": metadata['sentiment_value'], 
                    "dialogue": metadata['dialogue'], 
                    "section": metadata['section']
                } for filename, metadata in filtered_sound_files.items()
            ], indent=2)}

            ADDITIONAL GUIDANCE:
            - DO NOT select any sound that is already in the current playback queue
            - Deeply consider how the dialogues resonate with the Ashari's current cultural state
            - The chosen sound should align with the current performance section theme
            - The sound should feel like a profound cultural reflection appropriate for this moment
            """
        
        # Prepare input data for logging
        input_data = {
            "word": word,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "cultural_context": cultural_context,
            "current_queue": current_queue
        }
        
        try:
            # Call GPT to select the sound file
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=50  # We only want the filename
            )
            
            # Extract the filename
            selected_filename = response.choices[0].message.content.strip()
            
            # Log the interaction
            self._log_gpt_interaction(
                interaction_type="sound_selection", 
                input_data=input_data, 
                response=selected_filename
            )
            
            # Validate the filename
            if selected_filename == "N/A":
                print(f"⚠️ No suitable sound file found for '{word}'")
                return None
            
            if selected_filename in self.sound_files:
                if selected_filename in current_queue:
                    print(f"⚠️ GPT selected a sound already in the queue: {selected_filename}")
                    # Find an alternative that's not in the queue
                    available_sounds = [f for f in filtered_sound_files.keys() if f not in current_queue]
                    if available_sounds:
                        import random
                        alternative = random.choice(available_sounds)
                        print(f"🔄 Using alternative sound instead: {alternative}")
                        return alternative
                    else:
                        print(f"Using the suggested sound despite queue duplication: {selected_filename}")
                else:
                    print(f"🎵 GPT selected sound file: {selected_filename} for '{word}' in {cultural_context.get('current_section', 'unknown')} section")
                return selected_filename
            else:
                print(f"⚠️ Invalid sound file selected: {selected_filename}")
                
                # Fallback: select a random sound from the filtered list that's not in the queue
                filtered_not_in_queue = [f for f in filtered_sound_files.keys() if f not in current_queue]
                if filtered_not_in_queue:
                    import random
                    fallback = random.choice(filtered_not_in_queue)
                    print(f"Using fallback sound: {fallback}")
                    return fallback
                return None
        
        except Exception as e:
            # Log any errors
            self._log_gpt_interaction(
                interaction_type="sound_selection_error", 
                input_data=input_data, 
                response=str(e)
            )
            print(f"Error in sound file selection: {e}")
            return None
    
    def queue_sounds(self, word: str, cultural_context: dict = None):
        """
        Queue appropriate sound files for a given word
        
        :param word: Input word to find matching sounds
        :param cultural_context: Optional additional context about the cultural interpretation
        """
        # Check if we're past the end of the End section
        from performance_clock import get_clock
        current_time = get_clock().get_elapsed_seconds()
        current_section = self._get_current_section(current_time)
        
        # If we're in the End section and past its end_seconds, don't add more clips
        if current_section and current_section["section_name"] == "End":
            end_section_end_time = current_section.get("end_time_seconds", float('inf'))
            if current_time >= end_section_end_time:
                print(f"🛑 Performance has ended (time: {current_time:.1f}s, End section end: {end_section_end_time:.1f}s)")
                print(f"🛑 No more clips can be added to the queue")
                return None
        
        # Special handling for "begin"
        if word.lower() == "begin":
            # Ensure intro.mp3 is added to the queue if it's not already there
            with self._playback_lock:
                if "intro.mp3" not in self.playback_queue:
                    self.playback_queue.insert(0, "intro.mp3")
                    print(f"🎬 Starting performance with initial sound: intro.mp3")
                    self._print_queue("Initial sound added for performance start")
        
        # Use GPT to select the most appropriate sound file
        selected_sound = self.select_sound_with_gpt(word, cultural_context)
        
        # If no sound is selected, attempt to add a default sound for the current section
        if selected_sound is None or selected_sound == "None":
            # Get current time from performance clock
            current_time = get_clock().get_elapsed_seconds()
            current_section = self._get_current_section(current_time)
            
            if current_section:
                # Map performance section to sound section
                sound_section = current_section['section_name']
                
                # Find sounds in the appropriate section
                section_sounds = [
                    filename for filename, metadata in self.sound_files.items()
                    if metadata.get('section', '') == sound_section
                ]
                
                if section_sounds:
                    # Choose a random sound from the appropriate section
                    import random
                    selected_sound = random.choice(section_sounds)
                    print(f"🎵 Added default sound {selected_sound} for section {sound_section}")
                    self._print_queue(f"Default sound added for {sound_section}")
                else:
                    # Fallback to a generic sound if no section-specific sounds found
                    if self.sound_files:
                        selected_sound = list(self.sound_files.keys())[0]
                        print("⚠️ No appropriate sounds found, using first available sound")
                        self._print_queue("Fallback sound added")
                    else:
                        print("❌ No sounds available at all!")
                        return None
        
        # If still no sound, log and return
        if selected_sound is None or selected_sound == "None":
            print("❌ No sounds available to play")
            return None
        
        # Add the selected sound to the playback queue
        with self._playback_lock:
            # Check if queue is empty before adding
            if not self.playback_queue:
                self.playback_queue.append(selected_sound)
                print(f"🎶 Added sound to empty queue: {selected_sound}")
                self._print_queue("Sound added to empty queue")
            elif selected_sound not in self.playback_queue:
                # Only add if not already in queue
                self.playback_queue.append(selected_sound)
                print(f"🎶 Added sound to queue: {selected_sound}")
                self._print_queue("Sound added to queue")
            else:
                print(f"⚠️ Sound {selected_sound} already in queue, not adding again")
                self._print_queue("No change - sound already in queue")
        
        # Ensure playback is running
        if not (self._playback_thread and self._playback_thread.is_alive()):
            self.start_playback()
        
        return selected_sound
    
    def _log_gpt_interaction(self, interaction_type: str, input_data: dict, response: str = None):
        """Log GPT interaction details"""
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(self.log_dir, f"gpt_log_{interaction_type}_{timestamp}.json")
        
        # Prepare log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "interaction_type": interaction_type,
            "input": input_data,
            "response": response
        }
        
        # Write to log file
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2)
            print(f"✅ Logged GPT interaction to {filename}")
        except Exception as e:
            print(f"❌ Error logging GPT interaction: {e}")

    def print_channel_status(self):
        """Print the status of all pygame mixer channels to diagnose playback issues"""
        print("\n🔊 CHANNEL STATUS REPORT:")
        print(f"Total channels: {pygame.mixer.get_num_channels()}")
        
        busy_channels = 0
        main_queue_channels = 0
        climax_channels = 0
        untracked_channels = 0
        
        for i in range(pygame.mixer.get_num_channels()):
            channel = pygame.mixer.Channel(i)
            is_busy = channel.get_busy()
            volume = channel.get_volume()
            
            if is_busy:
                busy_channels += 1
                
                # Determine if this channel belongs to main queue (0-15)
                if i < 16:
                    main_queue_channels += 1
                    print(f"  Channel {i}: BUSY (vol={volume:.2f}) - Main Queue")
                # Or if it belongs to climax system (16-31)
                elif 16 <= i < 32:
                    climax_channels += 1
                    print(f"  Channel {i}: BUSY (vol={volume:.2f}) - Climax System")
                else:
                    untracked_channels += 1
                    print(f"  Channel {i}: BUSY (vol={volume:.2f}) - Untracked")
        
        print(f"Busy channels: {busy_channels}/{pygame.mixer.get_num_channels()} ({busy_channels/pygame.mixer.get_num_channels()*100:.1f}%)")
        print(f"Main queue channels: {main_queue_channels}/16")
        print(f"Climax system channels: {climax_channels}/16")
        print(f"Untracked busy channels: {untracked_channels}")
        
        # Print details of actively tracked clips
        if hasattr(self, 'climax_system') and hasattr(self.climax_system, 'active_clips'):
            print(f"\nActive climax clips: {len(self.climax_system.active_clips)}")
        
        # Print crossfade info
        print("\nCrossfade Status:")
        if hasattr(self, '_current_sound') and self._current_sound:
            print(f"  Current sound: {self._current_sound}")
            
            # Calculate time remaining
            if hasattr(self, '_current_sound_end_time'):
                time_remaining = self._current_sound_end_time - time.time()
                print(f"  Time remaining: {time_remaining:.1f}s")
                if time_remaining <= 5.0:
                    print(f"  ⚠️ Crossfade should be active!")
        else:
            print("  No active sound")
            
        print(f"Current playback queue: {len(self.playback_queue)} items")
        if self.playback_queue:
            print("  Queue contents:")
            for i, sound in enumerate(self.playback_queue):
                print(f"    {i+1}. {sound}")
        print("-" * 40)
    
    def stop_sounds(self):
        """
        Stop current sound playback
        """
        # Signal the playback thread to stop
        self._stop_playback.set()
        
        # Stop all pygame sounds
        pygame.mixer.stop()
        
        # Wait for the thread to finish if it exists
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1)

    def _print_queue(self, action_message="Queue updated"):
        """Print the current queue with a custom message"""
        with self._playback_lock:
            print(f"\n🎶 {action_message}:")
            if not self.playback_queue:
                print("  Queue is empty.")
            else:
                for i, sound in enumerate(self.playback_queue, 1):
                    print(f"  {i}. {sound}")
    
    def clear_queue(self):
        """Clear the sound playback queue"""
        with self._playback_lock:
            self.playback_queue.clear()
            self._print_queue("Queue cleared manually")
    
    def get_sound_dialogue(self, sound_file: str) -> str:
        """
        Retrieve the dialogue for a specific sound file
        
        :param sound_file: Filename of the sound
        :return: Dialogue text or empty string if not found
        """
        return self.sound_files.get(sound_file, {}).get('dialogue', '')