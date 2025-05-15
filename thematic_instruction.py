import json
import time
import threading
import requests
from datetime import datetime

# Path to performance model file
PERFORMANCE_MODEL_PATH = "data/performance_model.json"

class ThematicInstructionSender:
    """
    Class to send thematic elements from performance model to voice modules
    at specific points in the performance timeline.
    """
    
    def __init__(self, api_url="http://localhost:3000"):
        """Initialize with API URL and load performance model"""
        self.api_url = api_url
        self.performance_model = None
        self.start_time = None
        self.timer_thread = None
        self.is_running = False
        self.load_performance_model()
        
        # Track which thematic elements have been sent
        self.sent_thematic_elements = set()
        
    def load_performance_model(self):
        """Load the performance model from the JSON file"""
        try:
            with open(PERFORMANCE_MODEL_PATH, 'r') as file:
                self.performance_model = json.load(file)
                print("Performance model loaded successfully.")
                print(f"Total duration: {self.performance_model['total_duration_seconds']} seconds")
                print(f"Sections: {[s['section_name'] for s in self.performance_model['sections']]}")
                return True
        except Exception as e:
            print(f"Error loading performance model: {e}")
            self.performance_model = None
            return False
            
    def start(self):
        """Start the thematic instruction sender"""
        if not self.performance_model:
            print("Cannot start: No performance model loaded.")
            return False
            
        self.start_time = time.time()
        self.is_running = True
        self.sent_thematic_elements = set()  # Reset the sent elements tracking
        
        # Start the timer thread
        self.timer_thread = threading.Thread(target=self._monitor_timeline)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        
        print(f"Thematic instruction sender started at {datetime.now().strftime('%H:%M:%S')}")
        return True
        
    def stop(self):
        """Stop the thematic instruction sender"""
        self.is_running = False
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1.0)
        print("Thematic instruction sender stopped")
        
    def _monitor_timeline(self):
        """Monitor the performance timeline and send thematic elements at appropriate times"""
        if not self.performance_model:
            return
            
        # Create a list of all time points where we need to send thematic elements
        time_points = []
        
        for section in self.performance_model["sections"]:
            # Skip sections without thematic elements
            if "thematic_elements" not in section:
                continue
                
            section_name = section["section_name"]
            thematic_elements = section["thematic_elements"]
            
            # Add start point if it has thematic element
            if "start" in thematic_elements:
                time_points.append({
                    "time": section["start_seconds"],
                    "section": section_name,
                    "point_type": "start",
                    "text": thematic_elements["start"]
                })
                
            # Add midpoint if it exists and has thematic element
            if "midpoint_seconds" in section and "midpoint" in thematic_elements:
                time_points.append({
                    "time": section["midpoint_seconds"],
                    "section": section_name,
                    "point_type": "midpoint",
                    "text": thematic_elements["midpoint"]
                })
                
            # Add climax if it exists and has thematic element
            if "climax_seconds" in section and "climax" in thematic_elements:
                time_points.append({
                    "time": section["climax_seconds"],
                    "section": section_name,
                    "point_type": "climax",
                    "text": thematic_elements["climax"]
                })
                
            # Add end point if it has thematic element (some use "end", others use "climax" for the end)
            if "end" in thematic_elements:
                time_points.append({
                    "time": section["end_seconds"],
                    "section": section_name,
                    "point_type": "end",
                    "text": thematic_elements["end"]
                })
        
        # Sort time points by time
        time_points.sort(key=lambda x: x["time"])
        
        print(f"Monitoring {len(time_points)} thematic instruction points:")
        for i, point in enumerate(time_points):
            print(f"{i+1}. {point['section']} {point['point_type']} at {point['time']}s")
        
        # Initialize tracking variables
        next_point_idx = 0
        check_interval = 0.5  # Check every half second
        
        # Main monitoring loop
        while self.is_running and next_point_idx < len(time_points):
            # Calculate elapsed time
            elapsed_time = time.time() - self.start_time
            
            # Get next time point
            next_point = time_points[next_point_idx]
            
            # Check if we've reached the next time point
            if elapsed_time >= next_point["time"]:
                # Create unique ID for this thematic element to track what's been sent
                point_id = f"{next_point['section']}_{next_point['point_type']}"
                
                # Only send if we haven't sent this element before
                if point_id not in self.sent_thematic_elements:
                    # Send the thematic element
                    self._send_thematic_element(
                        section=next_point["section"],
                        point_type=next_point["point_type"],
                        text=next_point["text"]
                    )
                    
                    # Mark as sent
                    self.sent_thematic_elements.add(point_id)
                    
                # Move to next time point
                next_point_idx += 1
            
            # Sleep until next check
            time.sleep(check_interval)
    
    def _send_thematic_element(self, section, point_type, text):
        """Send a thematic element to the voice modules"""
        endpoint = f"{self.api_url}/api/thematic-update"
        
        # Prepare the data payload
        data = {
            "section": section,
            "type": point_type,
            "text": text,
            "duration": 30  # Display for 30 seconds
        }
        
        try:
            print(f"\n🎭 SENDING THEMATIC ELEMENT: {section} {point_type}")
            print(f"Text: {text}")
            
            # Send to API
            response = requests.post(
                endpoint,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"✅ Thematic element sent successfully")
                return True
            else:
                print(f"❌ Error sending thematic element: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending thematic element: {e}")
            return False
            
    def send_manual_thematic(self, section, point_type, text=None):
        """Manually send a thematic element (useful for testing)"""
        # If text is not provided, try to get it from the performance model
        if text is None:
            for section_data in self.performance_model["sections"]:
                if section_data["section_name"] == section and "thematic_elements" in section_data:
                    if point_type in section_data["thematic_elements"]:
                        text = section_data["thematic_elements"][point_type]
                        break
            
            if text is None:
                print(f"❌ No thematic text found for {section} {point_type}")
                return False
        
        # Send the thematic element
        return self._send_thematic_element(section, point_type, text)

# Example usage
if __name__ == "__main__":
    sender = ThematicInstructionSender()
    
    # Test options
    print("\nOptions:")
    print("1. Start automatic timeline monitoring")
    print("2. Send a specific thematic element")
    print("3. Send all thematic elements (for testing)")
    print("4. Exit")
    
    choice = input("Enter your choice (1-4): ")
    
    if choice == "1":
        sender.start()
        print("Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sender.stop()
            
    elif choice == "2":
        sections = [s["section_name"] for s in sender.performance_model["sections"]]
        print("\nAvailable sections:")
        for i, section in enumerate(sections):
            print(f"{i+1}. {section}")
            
        section_idx = int(input(f"Enter section number (1-{len(sections)}): ")) - 1
        section = sections[section_idx]
        
        print("\nPoint types:")
        print("1. start")
        print("2. midpoint")
        print("3. climax")
        print("4. end")
        
        point_type_idx = int(input("Enter point type (1-4): ")) - 1
        point_types = ["start", "midpoint", "climax", "end"]
        point_type = point_types[point_type_idx]
        
        sender.send_manual_thematic(section, point_type)
        
    elif choice == "3":
        for section in sender.performance_model["sections"]:
            if "thematic_elements" not in section:
                continue
                
            section_name = section["section_name"]
            for point_type, text in section["thematic_elements"].items():
                if point_type in ["start", "midpoint", "climax", "end"]:
                    print(f"Sending {section_name} {point_type}...")
                    sender.send_manual_thematic(section_name, point_type, text)
                    time.sleep(2)  # Wait 2 seconds between sends
                    
    print("Done.")