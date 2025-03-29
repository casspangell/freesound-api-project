import random
import threading
import time
import pygame
import math

class ClimaxIntensitySystem:
    """
    System to handle increasing intensity during a specific time period
    by playing additional sound clips with decreasing intervals and tapered volume
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
        
        # Intensity time range (in seconds)
        self.start_time = 15.0  # Start at 15 seconds
        self.end_time = 120.0   # End at 2 minutes (120 seconds)
        
        # Intensity parameters
        self.initial_interval = 15.0  # Start with 15 seconds between clips
        self.final_interval = 2.0     # End with 2 seconds between clips
        
        # Volume parameters
        self.base_min_volume = 0.3   # Minimum volume at start of intensity period
        self.base_max_volume = 0.8   # Maximum volume at end of intensity period
        self.fade_duration = 0.7     # Fade duration in seconds (for both in and out)
        
        # Active clip tracking (for volume control)
        self.active_clips = {}  # {channel: {start_time, sound, base_volume}}
        
        # State tracking
        self.is_active = False
        self.last_clip_time = 0
    
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
        print(f"🔥 Climax intensity monitoring started (active from {self._format_time(self.start_time)} to {self._format_time(self.end_time)})")
        
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
                        print(f"🔥 Entering climax intensity zone ({self._format_time(current_time)})")
                    
                    # Calculate how far we are through the intensity period (0.0 to 1.0)
                    progress = (current_time - self.start_time) / (self.end_time - self.start_time)
                    
                    # Calculate current interval based on progress
                    # Start with longer intervals, end with shorter intervals
                    current_interval = self.initial_interval - progress * (self.initial_interval - self.final_interval)
                    
                    # Check if it's time to play a new clip
                    if current_time - self.last_clip_time >= current_interval:
                        self._play_random_climax_clip(progress)
                        self.last_clip_time = current_time
                
                # If we were active but now we're outside the zone
                elif self.is_active and current_time > self.end_time:
                    self.is_active = False
                    print(f"❄️ Exiting climax intensity zone ({self._format_time(current_time)})")
                
                # Sleep to avoid consuming too much CPU
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error in climax intensity monitoring: {e}")
                time.sleep(1.0)  # Sleep longer on error
    
    def _monitor_volume(self):
        """Background thread that manages volume tapering for clips"""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
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
                    
                    # Calculate elapsed time for this clip
                    elapsed = current_time - clip_info['start_time']
                    
                    # Get clip duration
                    duration = clip_info['sound'].get_length()
                    
                    # Calculate volume based on position
                    volume = self._calculate_tapered_volume(elapsed, duration, clip_info['base_volume'])
                    
                    # Set the new volume
                    channel.set_volume(volume)
                
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
            
            # Format progress and interval for logging
            progress_percent = int(progress * 100)
            current_interval = self.initial_interval - progress * (self.initial_interval - self.final_interval)
            
            print(f"🔉 Playing climax clip: {clip} (progress: {progress_percent}%, interval: {current_interval:.1f}s, volume: {base_volume:.1f})")
            
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