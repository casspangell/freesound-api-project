import threading
import time
import os
from performance_clock import get_clock
import movement

# Dictionary to track which section midpoints have already triggered movements
section_midpoints_triggered = {}

def setup_section_midpoint_monitors(performance_model, score_manager):
    """
    Set up monitoring for section midpoints to trigger movement scores.
    
    Args:
        performance_model (dict): The performance model containing section timings
        score_manager: The score manager instance for context
    """
    # Make sure we have sections to monitor
    if not performance_model or "sections" not in performance_model:
        print("⚠️ No valid performance model provided for midpoint monitoring")
        return
        
    # Extract all sections with midpoints
    sections_with_midpoints = []
    for section in performance_model["sections"]:
        if "midpoint_seconds" in section:
            sections_with_midpoints.append({
                "name": section["section_name"],
                "midpoint": section["midpoint_seconds"],
                "thematic_elements": section.get("thematic_elements", {})
            })
    
    if not sections_with_midpoints:
        print("⚠️ No sections with midpoints found in performance model")
        return
        
    print(f"🔄 Setting up movement monitors for {len(sections_with_midpoints)} section midpoints:")
    for section in sections_with_midpoints:
        print(f"  - {section['name']}: at {format_time(section['midpoint'])} seconds")
        # Initialize tracking for this section
        section_midpoints_triggered[section["name"]] = False
    
    # Start the monitoring thread
    monitor_thread = threading.Thread(
        target=monitor_section_midpoints,
        args=(sections_with_midpoints, score_manager),
        daemon=True
    )
    monitor_thread.start()
    print("✅ Section midpoint movement monitor started")

def monitor_section_midpoints(sections, score_manager):
    """
    Background thread that monitors for section midpoints and triggers movements.
    
    Args:
        sections (list): List of section data with midpoints
        score_manager: The score manager instance for context
    """
    # Initialize clock access
    clock = get_clock()
    
    # For debug logging
    last_log_time = 0
    log_interval = 30.0  # Log debug info every 30 seconds
    
    # Sort sections by midpoint time for efficient checking
    sections = sorted(sections, key=lambda s: s["midpoint"])
    
    print("🔍 Starting section midpoint monitoring...")
    
    while True:
        try:
            # Get current time
            current_time = clock.get_elapsed_seconds()
            
            # Periodic debug logging
            if current_time - last_log_time >= log_interval:
                print(f"🔍 Section midpoint monitor active - current time: {format_time(current_time)}")
                # Log upcoming midpoints
                upcoming = [s for s in sections if s["midpoint"] > current_time]
                if upcoming:
                    next_section = upcoming[0]
                    time_remaining = next_section["midpoint"] - current_time
                    print(f"  Next midpoint: {next_section['name']} in {format_time(time_remaining)} seconds")
                last_log_time = current_time
            
            # Check each section midpoint
            for section in sections:
                section_name = section["name"]
                midpoint_time = section["midpoint"]
                
                # If we're within 1 second of the midpoint and haven't triggered it yet
                if (abs(current_time - midpoint_time) < 1.0 and 
                    not section_midpoints_triggered.get(section_name, False)):
                    
                    # Mark as triggered
                    section_midpoints_triggered[section_name] = True
                    print(f"⚡ SECTION MIDPOINT REACHED: {section_name} at {format_time(current_time)}")
                    
                    # Get thematic element for this midpoint if available
                    theme = section.get("thematic_elements", {}).get("midpoint", "")
                    
                    # If no theme is available, use a default based on section name
                    if not theme:
                        theme = f"midpoint transition of {section_name}"
                    
                    # Generate the movement in a separate thread to avoid blocking
                    threading.Thread(
                        target=generate_midpoint_movement,
                        args=(section_name, theme, score_manager),
                        daemon=True
                    ).start()
            
            # Sleep to avoid consuming too much CPU
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error in section midpoint monitor: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5.0)  # Sleep longer on error

def generate_midpoint_movement(section_name, theme, score_manager):
    """
    Generate a movement score for a section midpoint and send it to webapp.
    
    Args:
        section_name (str): Name of the section hitting midpoint
        theme (str): Thematic element or description for this midpoint
        score_manager: The score manager instance for context
    """
    try:
        # Create a prompt that's informative but not too long
        # Extract key phrases from the theme (limit to ~50 characters)
        theme_extract = theme[:50] + "..." if len(theme) > 50 else theme
        
        # Create the movement prompt
        movement_prompt = f"Section {section_name} midpoint: {theme_extract}"
        print(f"🎭 Generating movement for: {movement_prompt}")
        
        # Call the movement generation function
        movement_score = movement.generate_movement_score(movement_prompt)
        
        print(f"✅ Generated midpoint movement for {section_name}: {movement_score}")
        
        # Movement generation already includes sending to webapp with TTS via
        # the movement.generate_movement_score function
        
    except Exception as e:
        print(f"❌ Error generating midpoint movement: {e}")
        import traceback
        traceback.print_exc()

def format_time(seconds):
    """Format seconds as MM:SS"""
    if seconds is None:
        return "00:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"