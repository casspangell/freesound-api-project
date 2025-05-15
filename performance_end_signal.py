import requests
import json
from stop_drone import send_drone_stop_command

def send_performance_end_signal(api_url="http://localhost:3000"):
    """
    Send a special signal to the web app to show the performance has ended
    This will display a message on all voice modules
    """
    endpoint = f"{api_url}/api/thematic-update"
    headers = {'Content-Type': 'application/json'}
    
    # Create a special end-of-performance signal
    end_signal = {
        "section": "End",
        "type": "performance_complete",
        "text": "The performance has concluded. Thank you for experiencing The Ashari consciousness.",
        "duration": 0,  # 0 means display indefinitely until manually cleared
        "is_final": True  # Special flag to indicate this is the final message
    }
    
    try:
        print(f"🎬 Sending END OF PERFORMANCE signal to web app")
        response = requests.post(endpoint, data=json.dumps(end_signal), headers=headers)
        response.raise_for_status()
        
        print(f"✅ End signal sent successfully: {response.status_code}")
        return response.json()
            
    except Exception as e:
        print(f"❌ Error sending end signal: {e}")
        return None

# Add this to score.py to be called after the final clip has played
def send_performance_completed_signal():
    """Send various signals to indicate the performance is complete"""
    # Stop all drone sounds
    stop_drone = send_drone_stop_command()
    
    # Send performance end signal
    end_signal = send_performance_end_signal()
    
    # Log completion
    print("🏁 PERFORMANCE COMPLETE - All signals sent")
    
    return {
        "drone_stop": stop_drone,
        "end_signal": end_signal
    }