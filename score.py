import json
import os
import threading
import time
from datetime import datetime
import ollama
import config
import pygame
import logging
from performance_clock import get_clock, get_time_str
from time_utils import convert_model_to_seconds, _format_time
from audiofile_manager import AudioFileManager
from sound_playback_manager import SoundPlaybackManager
from movement import generate_movement_score
from performance_end_signal import send_performance_end_signal, send_performance_completed_signal
from stop_drone import send_drone_stop_command

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

        # Create Ashari instance if not provided
        if ashari is None:
            from ashari import Ashari
            ashari = Ashari()
            ashari.load_state()
        
        # Store the Ashari instance
        self.ashari = ashari
        
        # Ensure log directory exists
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Load performance model
        self.performance_model = {}
        self._load_performance_model(performance_model_path)
        
        # Create audio file manager
        self.audio_manager = AudioFileManager(
            base_sound_path=base_sound_path,
            metadata_path=sound_files_path
        )
        
        # Get sound metadata from audio manager
        self.sound_files = self.audio_manager.sound_metadata
        
        # Start preloading sounds in background
        self.audio_manager.preload_all_sounds()
        
        # Create sound playback manager
        self.sound_manager = SoundPlaybackManager(audio_manager=self.audio_manager)
        self.sound_manager.parent_score_manager = self
        
        # Configure initial state
        self.repeat = repeat
        self._end_transition_played = False
        self._performance_ended = False

        # Add intro sound to queue
        self.sound_manager.add_to_queue("intro.mp3")
        
        # Cached section info
        self._current_section = None
        self._last_section_check_time = 0
        
        # Section transition monitoring thread
        self._section_monitor_thread = None
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
        sound_section = self.audio_manager.get_sound_section(sound_file)
        
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
        duration = self.audio_manager.get_sound_duration(current_sound)
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
            falling_clips = self.audio_manager.get_all_sounds_by_section("Falling Voices")
            
            if falling_clips:
                import random
                falling_clip = random.choice(falling_clips)
                print(f"🍂 Selected Falling Action clip: {falling_clip}")
                return falling_clip
        
        # Find all sounds from the target section
        section_sounds = self.audio_manager.get_all_sounds_by_section(target_section)
        
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
        # Start the sound manager's playback
        self.sound_manager.start_playback()
        
        # Start section transition monitoring thread
        self._stop_event.clear()
        self._section_monitor_thread = threading.Thread(target=self._monitor_section_transitions)
        self._section_monitor_thread.daemon = True
        self._section_monitor_thread.start()
        
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
    
    def _monitor_section_transitions(self):
        """Background thread that monitors section transitions"""
        from performance_clock import get_clock

        # Track the last known section
        last_section_name = None
        section_check_interval = 0.25  # Check every 1/4 second
        last_check_time = 0

        # Keep track of transitions we've already handled
        handled_sections = set()

        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Only check periodically to avoid excessive CPU usage
                if current_time - last_check_time < section_check_interval:
                    time.sleep(0.05)
                    continue
                    
                last_check_time = current_time
                
                # Get current performance time
                performance_time = get_clock().get_elapsed_seconds()
                
                # Get current section
                current_section = self._get_current_section(performance_time)
                if not current_section:
                    time.sleep(0.1)
                    continue
                    
                current_section_name = current_section["section_name"]
                
                # If section changed from previous check 
                if last_section_name != current_section_name:
                    print(f"📊 SECTION CHANGED to: {current_section_name} (at {_format_time(performance_time)})")
                    generate_movement_score(current_section_name)

                    # Check if queue is empty and add default clip for the new section
                    current_queue = self.sound_manager.get_queue()
                    
                    if not current_queue and current_section_name not in handled_sections:
                        # Find all clips for this section
                        section_clips = self.audio_manager.get_all_sounds_by_section(current_section_name)
                        
                        if section_clips:
                            # Choose one of the default clips for this section
                            import random
                            default_clip = random.choice(section_clips)
                            
                            # Add it to the queue
                            self.sound_manager.add_to_queue(default_clip, priority=True)
                            print(f"🎵 Added default clip for {current_section_name} section: {default_clip}")
                    
                    # Special handling for Bridge section
                    if current_section_name == "Bridge" and "Bridge" not in handled_sections:
                        print(f"🌉 BRIDGE SECTION DETECTED! Clearing queue and adding bridge_1.mp3")
                        generate_movement_score(current_section_name)
                        # Clear the queue and add the bridge clip
                        self.sound_manager.clear_queue()
                        self.sound_manager.add_to_queue("bridge_1.mp3", priority=True)
                        
                        # Mark section as handled
                        handled_sections.add("Bridge")
                        print("🌉 Bridge transition handling complete")
                    
                    # Special handling for End section
                    elif current_section_name == "End":
                        print(f"🏁 END SECTION DETECTED! Selecting appropriate ending sequence")
                        generate_movement_score(current_section_name)
                        # Clear the queue
                        self.sound_manager.clear_queue()
                        
                        # Add transition sound first
                        self.sound_manager.add_to_queue("end_transition.mp3", priority=True)
                        
                        # Get cultural context for the end selection
                        cultural_context = {
                            "performance_time": get_time_str(),
                            "performance_time_seconds": performance_time
                        }
                        
                        # Mark section as handled and set flag
                        handled_sections.add(current_section_name)
                        self._end_transition_played = True
                        print("🏁 End transition handling complete")

                    # Add special handling for Final section
                    elif current_section_name == "Final":
                        print(f"🎬 FINAL SECTION DETECTED! Playing end clip once only")
                        generate_movement_score(current_section_name)
                        # Set the performance ended flag
                        self._performance_ended = True
                        
                        # Mark section as handled
                        handled_sections.add(current_section_name)
                        
                        # Clear the queue to stop any currently queued sounds
                        self.sound_manager.clear_queue()
                        
                        # Get cultural context for the end selection
                        cultural_context = {
                            "performance_time": get_time_str(),
                            "performance_time_seconds": performance_time
                        }
                        
                        # Select the appropriate ending clip using GPT
                        end_clip = self.select_end_clip_with_gpt(cultural_context)
                        print(f"Selected end clip {end_clip}")
                        sound = self.audio_manager.get_sound(end_clip)
                        print(f"sound ++++ {end_clip}")

                        if end_clip and sound:
                            # Find a free channel
                            channel = pygame.mixer.find_channel()
                            if channel is None:
                                print("⚠️ No available channel, trying to force-free one")
                                # No channels available, try freeing one
                                for i in range(pygame.mixer.get_num_channels()):
                                    ch = pygame.mixer.Channel(i)
                                    if ch.get_busy():
                                        print(f"  Stopping sound on channel {i} to make room")
                                        ch.stop()
                                        break
                                channel = pygame.mixer.find_channel()

                            # Play the sound if we found a channel
                            if channel:
                                # Use a better volume
                                channel.set_volume(1.0)
                                self.sound_manager.play_sound(channel, sound, end_clip)
                                print(f"▶️ Playing Final Clip ONCE ONLY: {end_clip}")

                                sound_duration = sound.get_length()
        
                                # Create a timer to send the completion signal after the sound finishes
                                def send_completion_after_sound():
                                    # Wait for sound duration plus a small buffer
                                    time.sleep(sound_duration + 1.0)
                                    # Send the performance completed signal
                                    print("🏁 Final sound has finished playing - sending completion signal")
                                    send_performance_completed_signal()
                                
                                # Start the timer in a separate thread
                                completion_thread = threading.Thread(target=send_completion_after_sound)
                                completion_thread.daemon = True
                                completion_thread.start()
                            else:
                                print("❌ CRITICAL: Still no available channel after attempting to free one")

                        else:
                            print(f"❌ CRITICAL: Could not load final clip: {end_clip}")
                            
                        print("✅ Final section handling complete - will not repeat")
                    
                    # Update last known section
                    last_section_name = current_section_name
                
                # Sleep to avoid consuming too much CPU
                time.sleep(0.1)
        
            except Exception as e:
                print(f"Error in section transition monitoring: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1.0)  # Sleep longer on error

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
        current_queue = self.sound_manager.get_queue()
        
        # Construct the system prompt
        system_prompt = """
            You are the Sound Selector for the Ashari cultural narrative. Your task is to choose the most thematically and emotionally appropriate sound file based on the given keyword and cultural context, specifically from the available sound files within the current section of the performance.

            REQUIREMENTS:
            1. ALWAYS return a VALID FILENAME from the available sound files within the **current section**.
            2. Use the **dialogue section** as the primary method of selection.
            3. Consider both the **current cultural memory** and the **performance timeline position**.
            4. Match the sound file's dialogue to the input word's emotional and cultural resonance.
            5. Select sounds that align with the **current section** of the performance (e.g., intro, middle, climactic).
            6. DO NOT select any sound that is already in the **current playback queue**.

            Selection Criteria:
            - IMPORTANT: **Select only from the available sound files** in the **current section** of the performance.
            - Avoid selecting any sound file that is **already in the current playback queue**.
            - If a specific sound section is provided (e.g., **intro**, **middle**, **climactic**), **prefer sounds from that section**.
            - Analyze how each sound file's dialogue connects to:
              a) The input keyword
              b) The current cultural sentiment
              c) The strongest cultural values
              d) The current performance theme
            - Prioritize dialogues that:
              - Reflect the **emotional nuance** of the keyword.
              - Align with the **Ashari's current cultural stance**.
              - Match the **current performance section's thematic elements**.
              - Provide **depth and context** to the cultural experience.

            Evaluation Process:
            1. Read each dialogue carefully.
            2. Compare the dialogue's themes to the keyword and cultural context.
            3. Consider the **sentiment value** as a secondary factor.
            4. Select the file that most profoundly captures the moment's **emotional** and **cultural significance** within the **current performance section**.

            OUTPUT FORMAT:
            - Respond ONLY with the **EXACT filename** of the chosen sound file.
            - **NO additional explanation or text**.
            - If no perfect match exists, choose the closest thematic representation.

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
            response = ollama.chat(
                model="llama3.2", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
        
            sentiment_text = response['message']['content'].strip()

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

    def select_end_clip_with_gpt(self, cultural_context: dict = None) -> str:

        # Get all end section clips
        end_clips = self.audio_manager.get_all_sounds_by_section("End")

        import random
        fallback = random.choice(end_clips)
        print(f"Using ending clip: {fallback}")
        return fallback
    
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
        
        # Check if end transition has played - if so, don't allow new clips
        if self._end_transition_played:
            print("🏁 End transition has already played - no more clips can be added")
            return None

        # If we're in the End section and past its end_seconds, or the performance ended flag is set
        # don't add more clips
        if self._performance_ended or (current_section and current_section["section_name"] == "End"):
            end_section_end_time = current_section.get("end_time_seconds", float('inf'))
            if current_time >= end_section_end_time:
                self._performance_ended = True  # Set the flag for future use
                print(f"🛑 Performance has ended (time: {current_time:.1f}s, End section end: {end_section_end_time:.1f}s)")
                print(f"🛑 No more clips can be added to the queue")
                return None
        
        # Special handling for "begin"
        if word.lower() == "begin":
            # Ensure intro.mp3 is added to the queue if it's not already there
            current_queue = self.sound_manager.get_queue()
            if "intro.mp3" not in current_queue:
                self.sound_manager.add_to_queue("intro.mp3", priority=True)
                print(f"🎬 Starting performance with initial sound: intro.mp3")
        
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
                section_sounds = self.audio_manager.get_all_sounds_by_section(sound_section)
                
                if section_sounds:
                    # Choose a random sound from the appropriate section
                    import random
                    selected_sound = random.choice(section_sounds)
                    print(f"🎵 Added default sound {selected_sound} for section {sound_section}")
                else:
                    # Fallback to a generic sound if no section-specific sounds found
                    if self.sound_files:
                        selected_sound = list(self.sound_files.keys())[0]
                        print("⚠️ No appropriate sounds found, using first available sound")
                    else:
                        print("❌ No sounds available at all!")
                        return None
        
        # If still no sound, log and return
        if selected_sound is None or selected_sound == "None":
            print("❌ No sounds available to play")
            return None
        
        # Add the selected sound to the playback queue
        current_queue = self.sound_manager.get_queue()
        if not current_queue:
            self.sound_manager.add_to_queue(selected_sound)
        elif selected_sound not in current_queue:
            # Only add if not already in queue
            self.sound_manager.add_to_queue(selected_sound)
        else:
            print(f"⚠️ Sound {selected_sound} already in queue, not adding again")
        
        # Ensure playback is running
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

    # def print_channel_status(self):
    #     """Print the status of all pygame mixer channels to diagnose playback issues"""
    #     # Delegate to sound manager
    #     if hasattr(self.sound_manager, 'print_channel_status'):
    #         self.sound_manager.print_channel_status()
    #     else:
    #         print("\n🔊 CHANNEL STATUS REPORT:")
    #         print(f"Total channels: {pygame.mixer.get_num_channels()}")
            
    #         busy_channels = 0
    #         for i in range(pygame.mixer.get_num_channels()):
    #             channel = pygame.mixer.Channel(i)
    #             is_busy = channel.get_busy()
    #             volume = channel.get_volume()
                
    #             if is_busy:
    #                 busy_channels += 1
    #                 print(f"  Channel {i}: BUSY (vol={volume:.2f})")
            
    #         print(f"Busy channels: {busy_channels}/{pygame.mixer.get_num_channels()} ({busy_channels/pygame.mixer.get_num_channels()*100:.1f}%)")
    #         print(f"Current queue: {self.sound_manager.get_queue()}")
    #         print("-" * 40)
    
    def stop_sounds(self):
        """Stop current sound playback"""
        # Delegate to sound manager
        self.sound_manager.stop_playback()
        
        # Stop section monitor thread
        self._stop_event.set()
        if self._section_monitor_thread and self._section_monitor_thread.is_alive():
            self._section_monitor_thread.join(timeout=1)
    
    def clear_queue(self):
        """Clear the sound playback queue"""
        self.sound_manager.clear_queue()
    
    def get_sound_dialogue(self, sound_file: str) -> str:
        """
        Retrieve the dialogue for a specific sound file
        
        :param sound_file: Filename of the sound
        :return: Dialogue text or empty string if not found
        """
        if sound_file in self.sound_files:
            return self.sound_files[sound_file].get('dialogue', '')
        return ''
    
    def cleanup(self):
        """Clean up resources when shutting down"""
        # Stop playback
        self.stop_sounds()
        
        # Stop background loaders
        if hasattr(self.audio_manager, 'stop_background_loader'):
            self.audio_manager.stop_background_loader()
        
        # Stop any pygame resources
        pygame.mixer.quit()
        
        print("🧹 Ashari Score Manager cleaned up")