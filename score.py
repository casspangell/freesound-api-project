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

class AshariScoreManager:
    def __init__(self, 
                 ashari=None,
                 repeat=False,
                 sound_files_path='/data/sound_files.json', 
                 performance_model_path='/data/performance_model.json',
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
        self.playback_queue = ["1-7.mp3"]
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
        self._stop_playback = threading.Event()
        
        print(f"🎵 Ashari Score Manager initialized with {len(self.sound_files)} sound files")

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
        # Possible paths for performance model JSON
        possible_paths = [
            performance_model_path,
            os.path.join(os.path.dirname(__file__), performance_model_path),
            os.path.join(os.path.dirname(__file__), 'data/performance_model.json'),
            '/data/performance_model.json',
            'performance_model.json'
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self.performance_model = json.load(f)
                        
                        # Add seconds values for easier time comparison
                        for section in self.performance_model["sections"]:
                            # Convert time strings to seconds (format: "MM:SS")
                            for time_key in ["start_time", "end_time"]:
                                if time_key in section:
                                    min_sec = section[time_key].split(":")
                                    section[f"{time_key}_seconds"] = int(min_sec[0]) * 60 + int(min_sec[1])
                            
                            # Convert midpoint and climax if they exist
                            for special_time in ["midpoint_time", "climax_time"]:
                                if special_time in section:
                                    min_sec = section[special_time].split(":")
                                    section[f"{special_time}_seconds"] = int(min_sec[0]) * 60 + int(min_sec[1])
                        
                        print(f"✅ Loaded performance model from {path}")
                        return
            except Exception as e:
                print(f"❌ Error trying to load performance model from {path}: {e}")
        
        print("⚠️ WARNING: Could not find performance_model.json, using default values")
        # Create a simple default model if file not found
        self.performance_model = {
            "total_duration_seconds": 1080,  # 18 minutes
            "sections": [
                {
                    "section_name": "Rising Action",
                    "start_time": "0:00",
                    "start_time_seconds": 0,
                    "end_time": "6:00",
                    "end_time_seconds": 360,
                    "thematic_elements": {
                        "start": "Establishing the narrative foundation",
                        "midpoint": "Building connections",
                        "end": "Approaching a dramatic shift"
                    }
                },
                {
                    "section_name": "Bridge",
                    "start_time": "6:00",
                    "start_time_seconds": 360,
                    "end_time": "12:00",
                    "end_time_seconds": 720,
                    "thematic_elements": {
                        "start": "Moment of tension",
                        "midpoint": "Processing change",
                        "end": "Finding new direction"
                    }
                },
                {
                    "section_name": "Falling Action",
                    "start_time": "12:00",
                    "start_time_seconds": 720,
                    "end_time": "18:00",
                    "end_time_seconds": 1080,
                    "thematic_elements": {
                        "start": "New understanding emerges",
                        "midpoint": "Integration of experience",
                        "end": "Final reflection and resolution"
                    }
                }
            ]
        }
    
    def _load_sound(self, filename: str) -> pygame.mixer.Sound:
        """Load a sound file with the correct section-based path"""
        if filename is None:
            print("⚠️ Cannot load sound: filename is None")
            return None
        
        if filename in self._sound_cache:
            return self._sound_cache[filename]
        
        # Find the section for this filename
        section = next(
            (metadata['section'] for file, metadata in self.sound_files.items() if file == filename), 
            'narrative'  # default section if not found
        )
        
        # Try multiple possible paths
        possible_paths = [
            os.path.join(self.base_sound_path, section, filename),
            os.path.join(self.base_sound_path, 'narrative', filename),
            os.path.join('data/sound_files', section, filename),
            os.path.join('data/sound_files', 'narrative', filename),
            os.path.join('data/sound_files/narrative', filename),
            os.path.join('narrative', filename),
            filename
        ]
        
        for full_path in possible_paths:
            try:
                if os.path.exists(full_path):
                    sound = pygame.mixer.Sound(full_path)
                    
                    # Cache the sound
                    self._sound_cache[filename] = sound
                    return sound
            except Exception as e:
                pass  # Try next path
        
        print(f"⚠️ Sound file not found in any expected location: {filename}")
        return None

    def _continuous_playback(self):
        """Continuously play sounds in the playback queue"""
        import haiku
        
        while not self._stop_playback.is_set():
            # Check if playback queue is empty
            if not self.playback_queue:
                time.sleep(0.1)
                continue
            
            # First, do some housekeeping - make sure we have enough channels
            if pygame.mixer.get_num_channels() < 32:
                pygame.mixer.set_num_channels(32)
                print(f"Increased sound channels to {pygame.mixer.get_num_channels()}")
            
            # Count busy channels to check system state
            busy_count = sum(1 for i in range(pygame.mixer.get_num_channels()) if pygame.mixer.Channel(i).get_busy())
            if busy_count > pygame.mixer.get_num_channels() - 5:
                print(f"WARNING: {busy_count}/{pygame.mixer.get_num_channels()} channels busy, freeing resources")
                # Stop some sounds to free up channels
                for i in range(pygame.mixer.get_num_channels()):
                    if pygame.mixer.Channel(i).get_busy():
                        pygame.mixer.Channel(i).stop()
                        break
            
            # Get the next sound file
            with self._playback_lock:
                if not self.playback_queue:
                    continue
                sound_file = self.playback_queue.pop(0)
            
            # Load the sound
            sound = self._load_sound(sound_file)
            
            if sound:
                # Get metadata for logging
                metadata = self.sound_files.get(sound_file, {})
                
                logging.info(f"Playing sound: {sound_file}")
                
                # Force playback by finding a free channel or freeing one
                channel = pygame.mixer.find_channel()
                if channel is None:
                    # No channels available, stop the oldest sound
                    print("⚠️ No channels available - stopping oldest sound")
                    pygame.mixer.Channel(0).stop()  # Stop the first channel
                    channel = pygame.mixer.find_channel()
                
                # Double-check we have a channel
                if channel:
                    channel.set_volume(0.8)
                    channel.play(sound)
                    
                    # Check if there's dialogue, and if so, generate TTS haiku from it
                    # dialogue = metadata.get('dialogue', '')
                    # if dialogue and dialogue.strip():
                    #     try:
                    #         if not self.repeat:
                    #             # Process the entire dialogue directly
                    #             print(f"Processing dialogue: '{dialogue[:50]}...'")
                    #             # Generate the haiku in a separate thread to avoid blocking
                    #             haiku_thread = threading.Thread(
                    #                 target=haiku.generate_tts_haiku, 
                    #                 args=(dialogue,)
                    #             )
                    #             haiku_thread.daemon = True
                    #             haiku_thread.start()
                    #     except Exception as e:
                    #         print(f"Error generating haiku from dialogue: {e}")
                else:
                    # Emergency fallback - stop all sounds and try again
                    print("❗ EMERGENCY: Stopping all sounds to free channels")
                    pygame.mixer.stop()
                    # Try once more
                    channel = pygame.mixer.find_channel()
                    if channel:
                        channel.play(sound)
                    else:
                        print("💥 CRITICAL: Still no channel available after emergency stop")
                        # Add sound back to queue and continue
                        with self._playback_lock:
                            self.playback_queue.insert(0, sound_file)
                        time.sleep(0.5)
                        continue
                
                # Wait and manage multiple sounds
                start_time = time.time()
                duration = metadata.get('duration_seconds', 1)
                
                # Simplify playback management - don't try to overlap sounds as much
                while (time.time() - start_time) < duration * 0.9:  # 90% of duration to avoid overlap issues
                    if self._stop_playback.is_set():
                        if channel.get_busy():
                            channel.stop()
                        return
                    time.sleep(0.1)
                
                # If no sounds in queue, re-add the current sound
                with self._playback_lock:
                    if not self.playback_queue:
                        # Always add the current sound back to the queue if empty
                        print(f"Adding {sound_file} back to queue (queue is empty)")
                        self.playback_queue.insert(0, sound_file)
                    
                    # Print remaining playback queue
                    if self.playback_queue:
                        print("\n🎶 Remaining Playback Queue:")
                        for i, remaining_sound in enumerate(self.playback_queue, 1):
                            print(f"  {i}. {remaining_sound}")
                    else:
                        print("  Queue is now empty.")

    def start_playback(self):
        """Start continuous playback thread if not already running"""
        # Ensure only one playback thread is running
        if self._playback_thread and self._playback_thread.is_alive():
            return
        
        # Reset stop flag
        self._stop_playback.clear()
        
        # Start playback thread
        self._playback_thread = threading.Thread(target=self._continuous_playback)
        self._playback_thread.daemon = True  # Make thread exit when main program exits
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
        
        return None
    
    def _calculate_section_progress(self, current_time_seconds: float, section):
        """Calculate progress through the current section (0.0 to 1.0)"""
        section_start = section["start_time_seconds"]
        section_end = section["end_time_seconds"]
        section_duration = section_end - section_start
        
        if section_duration <= 0:
            return 0.0
        
        progress = (current_time_seconds - section_start) / section_duration
        return max(0.0, min(1.0, progress))  # Clamp between 0 and 1
    
    def _map_performance_section_to_sound_section(self, performance_section: str) -> str:
        """Map performance section names to sound file section categories"""
        section_mapping = {
            "Rising Action": "intro",
            "Bridge": "middle",
            "Falling Action": "climactic"
        }
        
        return section_mapping.get(performance_section, "middle")

    def select_sound_with_gpt(self, word: str, cultural_context: dict = None) -> str:
        """
        Select a sound using GPT, enhanced with performance timeline awareness
        
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
        performance_context = {}
        if current_section:
            section_progress = self._calculate_section_progress(current_time_seconds, current_section)
            section_name = current_section["section_name"]
            
            performance_context = {
                "performance_time": get_time_str(),
                "performance_time_seconds": current_time_seconds,
                "current_section": section_name,
                "section_progress": section_progress
            }
            
            # Add thematic elements based on progress
            if "thematic_elements" in current_section:
                themes = current_section["thematic_elements"]
                if section_progress < 0.33 and "start" in themes:
                    performance_context["current_theme"] = themes["start"]
                elif section_progress < 0.66 and "midpoint" in themes:
                    performance_context["current_theme"] = themes["midpoint"]
                elif "end" in themes:
                    performance_context["current_theme"] = themes["end"]
                elif "climax" in themes:
                    performance_context["current_theme"] = themes["climax"]
            
            # Filter sounds for appropriate section
            sound_section = self._map_performance_section_to_sound_section(section_name)
            
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
        
        # Construct the system prompt
        system_prompt = """
            You are the Sound Selector for the Ashari cultural narrative. Your task is to choose the most thematically and emotionally appropriate sound file based on the given keyword and cultural context.

            REQUIREMENTS:
            1. ALWAYS return a VALID FILENAME from the available sound files.
            2. Use the dialogue section as the primary method of selection.
            3. Consider both the current cultural memory and the performance timeline position.
            4. Match the sound file's dialogue to the input word's emotional and cultural resonance.
            5. Select sounds that align with the current section of the performance.

            Selection Criteria:
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
            - Deeply consider how the dialogues resonate with the Ashari's current cultural state
            - The chosen sound should align with the current performance section theme
            - The sound should feel like a profound cultural reflection appropriate for this moment
            """
        
        # Prepare input data for logging
        input_data = {
            "word": word,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "cultural_context": cultural_context
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
                print(f"🎵 GPT selected sound file: {selected_filename} for '{word}' in {cultural_context.get('current_section', 'unknown')} section")
                return selected_filename
            else:
                print(f"⚠️ Invalid sound file selected: {selected_filename}")
                
                # Fallback: select a random sound from the filtered list
                if filtered_sound_files:
                    fallback = list(filtered_sound_files.keys())[0]
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
        # Use GPT to select the most appropriate sound file
        selected_sound = self.select_sound_with_gpt(word, cultural_context)
        
        # If no sound is selected, handle gracefully
        if selected_sound is None:
            print(f"No sound file available for '{word}'")
            return None
        
        # Add the selected sound to the playback queue
        with self._playback_lock:
            # Append the new sound to the end of the existing queue
            self.playback_queue.append(selected_sound)
            
            # Print the current playback queue
            print("\n🎶 Current Playback Queue:")
            for i, sound in enumerate(self.playback_queue, 1):
                print(f"  {i}. {sound}")
        
        # Ensure playback is running - important change here
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
    
    def clear_queue(self):
        """
        Clear the sound playback queue
        """
        self.stop_sounds()
        self.playback_queue.clear()
    
    def get_sound_dialogue(self, sound_file: str) -> str:
        """
        Retrieve the dialogue for a specific sound file
        
        :param sound_file: Filename of the sound
        :return: Dialogue text or empty string if not found
        """
        return self.sound_files.get(sound_file, {}).get('dialogue', '')