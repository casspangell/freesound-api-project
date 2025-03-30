import random
import threading
import time
import pygame
import math
 
class ClimaxIntensitySystem:
     """
     System to handle increasing intensity during the midpoint to climax period
     of the Rising Action section, using the performance model for timing
     """

     def __init__(self, score_manager):
         # Store reference to score manager
         self.score_manager = score_manager

         # Climax clips to use (these will be played randomly during the climax approach)
         self.climax_clips = [f"1-{i}.mp3" for i in range(8, 26)]  # 1-8.mp3 through 1-25.mp3

         # Thread for monitoring and playing clips
         self.monitor_thread = None
         self.volume_thread = None
         self.stop_event = threading.Event()

         # Intensity parameters from performance model will be set during initialization
         self.start_time = None  # Will be set from model's midpoint
         self.end_time = None    # Will be set from model's climax

         # Intensity parameters - INCREASED FOR MORE INTENSITY
         self.initial_interval = 12.0  # Start with shorter intervals between clips
         self.final_interval = 1.0     # End with even shorter intervals

         # Add multi-clip support for higher intensity
         self.max_concurrent_clips = 3  # Allow up to 3 clips to play simultaneously

         # Volume parameters
         self.base_min_volume = 0.4   # Higher starting volume
         self.base_max_volume = 0.95  # Nearly full volume at peak
         self.fade_duration = 0.5     # Shorter, more dramatic fades

         # Active clip tracking (for volume control)
         self.active_clips = {}  # {channel: {start_time, sound, base_volume}}
         self.active_count = 0   # Track how many clips are currently playing

         # State tracking
         self.is_active = False
         self.last_clip_time = 0

         # Initialize the intensity period from the performance model
         self._initialize_from_performance_model()

     def _initialize_from_performance_model(self):
         """Initialize timing from the performance model"""
         try:
             # Get the performance model from the score manager
             performance_model = self.score_manager.performance_model

             if not performance_model or "sections" not in performance_model:
                 print("⚠️ No valid performance model found, using default values")
                 self.start_time = 15.0   # Default: Start at 15 seconds
                 self.end_time = 120.0    # Default: End at 2 minutes (120 seconds)
                 return

             # Find the Rising Action section
             rising_action = None
             for section in performance_model["sections"]:
                 if section["section_name"] == "Rising Action":
                     rising_action = section
                     break

             if not rising_action:
                 print("⚠️ No Rising Action section found in performance model, using default values")
                 self.start_time = 15.0
                 self.end_time = 120.0
                 return

             # Check if midpoint and climax are defined
             if "midpoint_time_seconds" in rising_action and "climax_time_seconds" in rising_action:
                 self.start_time = rising_action["midpoint_time_seconds"]
                 self.end_time = rising_action["climax_time_seconds"]

                 print(f"✅ Climax system initialized from performance model:")
                 print(f"   Intensity period: {self._format_time(self.start_time)} to {self._format_time(self.end_time)}")
             else:
                 # Calculate midpoint and climax if not explicitly defined
                 start = rising_action.get("start_seconds", 0)
                 end = rising_action.get("end_seconds", 600)  # Default 10 minutes if not specified

                 # Default to 40% and 80% through the section if exact points not specified
                 self.start_time = start + (end - start) * 0.4
                 self.end_time = start + (end - start) * 0.8

                 print(f"⚠️ Midpoint and climax not explicitly defined in model, calculated values:")
                 print(f"   Intensity period: {self._format_time(self.start_time)} to {self._format_time(self.end_time)}")

         except Exception as e:
             print(f"❌ Error initializing from performance model: {e}")
             # Fall back to default values
             self.start_time = 15.0
             self.end_time = 120.0
             print(f"   Using default intensity period: {self._format_time(self.start_time)} to {self._format_time(self.end_time)}")

     def start_monitoring(self):
         """Start the background monitoring thread"""
         if self.monitor_thread is not None and self.monitor_thread.is_alive():
             print("Climax monitoring already active")
             return

         # Reset stop event
         self.stop_event.clear()

         # Start monitoring thread
         self.monitor_thread = threading.Thread(target=self._monitor_timeline, daemon=True)
         self.monitor_thread.start()
         print(f"🔥 INTENSE Climax monitoring started (active from {self._format_time(self.start_time)} to {self._format_time(self.end_time)})")

         # Start volume control thread
         self.volume_thread = threading.Thread(target=self._monitor_volume, daemon=True)
         self.volume_thread.start()

     def stop_monitoring(self):
         """Stop the monitoring thread"""
         if self.monitor_thread is None or not self.monitor_thread.is_alive():
             return

         # Signal thread to stop
         self.stop_event.set()

         # Wait for thread to finish
         self.monitor_thread.join(timeout=1.0)
         self.monitor_thread = None
         self.is_active = False
         print("❄️ Climax intensity monitoring stopped")

     def _format_time(self, seconds):
         """Format seconds as MM:SS"""
         minutes = int(seconds // 60)
         secs = int(seconds % 60)
         return f"{minutes:02d}:{secs:02d}"

     def _monitor_timeline(self):
         """Background thread that monitors timeline position and triggers intensity clips"""
         from performance_clock import get_clock

         while not self.stop_event.is_set():
             try:
                 # Get current timeline position
                 current_time = get_clock().get_elapsed_seconds()

                 # Check if we're in the intensity period
                 if self.start_time <= current_time <= self.end_time:
                     # Transition to active state if we weren't already
                     if not self.is_active:
                         self.is_active = True
                         self.last_clip_time = current_time
                         print(f"🔥🔥🔥 ENTERING HIGH INTENSITY ZONE ({self._format_time(current_time)})")

                     # Calculate how far we are through the intensity period (0.0 to 1.0)
                     progress = (current_time - self.start_time) / (self.end_time - self.start_time)

                     # Calculate current interval based on progress
                     # Start with longer intervals, end with shorter intervals
                     current_interval = self.initial_interval - progress * (self.initial_interval - self.final_interval)

                     # Add variation to the interval (plus or minus 15%)
                     variation = (random.random() * 0.3) - 0.15  # -15% to +15%
                     adjusted_interval = max(0.5, current_interval * (1 + variation))

                     # Check if it's time to play a new clip and we're under the concurrent limit
                     # As we progress, allow more simultaneous clips
                     current_max_clips = 1 + int(progress * (self.max_concurrent_clips - 1))

                     if (current_time - self.last_clip_time >= adjusted_interval and 
                             self.active_count < current_max_clips):
                         self._play_random_climax_clip(progress)
                         self.last_clip_time = current_time

                 # If we were active but now we're outside the zone
                 elif self.is_active and current_time > self.end_time:
                     self.is_active = False
                     print(f"❄️ Exiting HIGH INTENSITY zone ({self._format_time(current_time)})")

                 # Sleep to avoid consuming too much CPU
                 time.sleep(0.25)  # More frequent checks for more accurate timing

             except Exception as e:
                 print(f"Error in climax intensity monitoring: {e}")
                 time.sleep(1.0)  # Sleep longer on error

     def _monitor_volume(self):
         """Background thread that manages volume tapering for clips"""
         while not self.stop_event.is_set():
             try:
                 current_time = time.time()
                 active_count = 0

                 # Make a copy of the keys to avoid modifying during iteration
                 channels_to_check = list(self.active_clips.keys())

                 for channel in channels_to_check:
                     if channel not in self.active_clips:
                         continue  # Skip if removed during iteration

                     clip_info = self.active_clips[channel]

                     # Skip if the channel is no longer busy
                     if not channel.get_busy():
                         del self.active_clips[channel]
                         continue

                     active_count += 1

                     # Calculate elapsed time for this clip
                     elapsed = current_time - clip_info['start_time']

                     # Get clip duration
                     duration = clip_info['sound'].get_length()

                     # Calculate volume based on position
                     volume = self._calculate_tapered_volume(elapsed, duration, clip_info['base_volume'])

                     # Set the new volume
                     channel.set_volume(volume)

                 # Update active count for the playback system
                 self.active_count = active_count

                 # Sleep to avoid consuming too much CPU
                 time.sleep(0.05)  # More frequent updates for smoother fades

             except Exception as e:
                 print(f"Error in volume monitoring: {e}")
                 time.sleep(0.5)  # Sleep longer on error

     def _calculate_tapered_volume(self, elapsed, duration, base_volume):
         """Calculate volume with tapering at start and end"""
         # Fade in period
         fade_in_duration = self.fade_duration

         # Fade out period
         fade_out_start = duration - self.fade_duration

         # Calculate the multiplier based on position
         if elapsed < fade_in_duration:
             # Fade in (0 to 1)
             multiplier = elapsed / fade_in_duration
         elif elapsed > fade_out_start:
             # Fade out (1 to 0)
             fade_out_progress = (elapsed - fade_out_start) / self.fade_duration
             multiplier = 1.0 - fade_out_progress
         else:
             # Full volume in the middle
             multiplier = 1.0

         # Use a smoother curve (sine) for more natural fading
         if multiplier < 1.0:
             # Convert linear 0-1 to sine curve for smoother fades
             multiplier = math.sin(multiplier * math.pi/2)

         # Apply multiplier to base volume
         return base_volume * multiplier

     def _play_random_climax_clip(self, progress):
         """Play a random clip from the climax collection with tapered volume"""
         try:
             # Select a random clip
             clip = random.choice(self.climax_clips)

             # Calculate base intensity volume based on progress (higher volume as we approach end)
             base_volume = self.base_min_volume + (progress * (self.base_max_volume - self.base_min_volume))

             # Add more dynamic variation to volume based on progress
             # As we get further into the climax zone, add more variation
             volume_variation = progress * 0.2  # Up to 20% variation at peak
             base_volume = base_volume * (1.0 + (random.random() * volume_variation - volume_variation/2))

             # Ensure volume stays in reasonable range
             base_volume = max(0.1, min(1.0, base_volume))

             # Format progress and interval for logging
             progress_percent = int(progress * 100)
             current_interval = self.initial_interval - progress * (self.initial_interval - self.final_interval)

             # More dramatic logging for higher intensity
             intensity_marker = "🔥" * (1 + int(progress * 3))  # More fire emojis as we progress
             print(f"{intensity_marker} Playing climax clip: {clip} (progress: {progress_percent}%, volume: {base_volume:.1f})")

             # Load the sound
             sound = self.score_manager._load_sound(clip)

             if sound:
                 # Find a free channel
                 channel = pygame.mixer.find_channel()
                 if channel is None:
                     # No channels available, try freeing one
                     for i in range(pygame.mixer.get_num_channels()):
                         ch = pygame.mixer.Channel(i)
                         if ch.get_busy():
                             ch.stop()
                             break
                     channel = pygame.mixer.find_channel()

                 # Play the sound if we found a channel
                 if channel:
                     # Start with low volume (will be controlled by the volume thread)
                     channel.set_volume(0.01)  # Start very quiet, will fade in
                     channel.play(sound)

                     # Add to active clips for volume control
                     # Use the channel object itself as the key
                     self.active_clips[channel] = {
                         'start_time': time.time(),
                         'sound': sound,
                         'base_volume': base_volume
                     }
                 else:
                     print("⚠️ No available channel for climax clip")
             else:
                 print(f"⚠️ Could not load climax clip: {clip}")

         except Exception as e:
             print(f"Error playing climax clip: {e}")
             import traceback
             traceback.print_exc()