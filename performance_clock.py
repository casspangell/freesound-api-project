import time
import threading

class PerformanceClock:
    """A clock to track performance time with minutes and seconds"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure only one clock instance exists"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PerformanceClock, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the clock (only runs once due to singleton pattern)"""
        if self._initialized:
            return
            
        self._start_time = None
        self._is_running = False
        self._elapsed_time = 0
        self._thread = None
        self._callbacks = []
        self._initialized = True
        
    def start(self):
        """Start the clock timer"""
        if not self._is_running:
            self._start_time = time.time() - self._elapsed_time
            self._is_running = True
            print(f"🕒 Performance clock started")
            
            # Start the update thread
            self._thread = threading.Thread(target=self._update_thread, daemon=True)
            self._thread.start()
            
    def stop(self):
        """Stop the clock timer"""
        if self._is_running:
            self._elapsed_time = time.time() - self._start_time
            self._is_running = False
            print(f"🕒 Performance clock stopped at {self.get_time_str()}")
    
    def reset(self):
        """Reset the clock timer to zero"""
        self.stop()
        self._elapsed_time = 0
        print(f"🕒 Performance clock reset")
    
    def get_elapsed_seconds(self):
        """Get the total elapsed seconds"""
        if self._is_running:
            return time.time() - self._start_time
        return self._elapsed_time
    
    def get_minutes(self):
        """Get elapsed minutes as an integer"""
        return int(self.get_elapsed_seconds() // 60)
    
    def get_seconds(self):
        """Get elapsed seconds (0-59) as an integer"""
        return int(self.get_elapsed_seconds() % 60)
    
    def get_time_str(self):
        """Get formatted time string (MM:SS)"""
        mins = self.get_minutes()
        secs = self.get_seconds()
        return f"{mins:02d}:{secs:02d}"
    
    def _update_thread(self):
        """Background thread that updates every second"""
        last_second = -1
        while self._is_running:
            current_second = self.get_seconds()
            if current_second != last_second:
                self._notify_callbacks()
                last_second = current_second
            time.sleep(0.1)  # Check frequently but not too CPU intensive
    
    def add_callback(self, callback_func):
        """Add a callback function that will be called every second
        The callback receives the clock instance as parameter"""
        self._callbacks.append(callback_func)
        
    def remove_callback(self, callback_func):
        """Remove a previously registered callback function"""
        if callback_func in self._callbacks:
            self._callbacks.remove(callback_func)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks"""
        for callback in self._callbacks:
            try:
                callback(self)
            except Exception as e:
                print(f"Error in clock callback: {e}")
    
    def is_running(self):
        """Check if the clock is currently running"""
        return self._is_running

# Convenience functions to access the singleton instance
def get_clock():
    """Get the global clock instance"""
    return PerformanceClock()

def start_clock():
    """Start the global clock"""
    get_clock().start()
    
def stop_clock():
    """Stop the global clock"""
    get_clock().stop()
    
def reset_clock():
    """Reset the global clock"""
    get_clock().reset()
    
def get_time_str():
    """Get formatted time string from global clock"""
    return get_clock().get_time_str()