import os
import json
import time
from movement import generate_movement_score
from haiku import send_haiku_to_webapp

def generate_midpoint_movement(ashari, section, current_time_seconds):
    """
    Generate a movement at a section's midpoint based on current Ashari state.
    
    Args:
        ashari (Ashari): Current Ashari instance
        section (dict): Current performance section
        current_time_seconds (float): Current time in performance
    
    Returns:
        dict: Movement generation details
    """
    try:
        # Log directory for movements
        os.makedirs('movement_scores', exist_ok=True)
        movement_log_path = 'movement_scores/section_midpoint_movements.log'
        
        # Capture the current state of cultural memory at this moment
        current_cultural_memory = dict(ashari.cultural_memory)
        
        # Identify the most extreme cultural value at this moment
        extreme_values = sorted(
            current_cultural_memory.items(), 
            key=lambda x: abs(x[1]), 
            reverse=True
        )
        
        # Select the most extreme value
        most_extreme_value, extreme_value_score = extreme_values[0]
        
        # Generate movement score based on the extreme value
        movement_score = generate_movement_score(most_extreme_value)
        
        # Prepare movement details
        movement_details = {
            "timestamp": int(time.time()),
            "performance_time_seconds": current_time_seconds,
            "section_name": section.get('section_name', 'Unknown'),
            "extreme_value": most_extreme_value,
            "extreme_value_score": extreme_value_score,
            "movement_score": movement_score,
            "cultural_memory_snapshot": current_cultural_memory
        }
        
        # Find the corresponding MP3 file
        movement_files = [
            f for f in os.listdir('movement_scores') 
            if f.endswith('.mp3') and most_extreme_value in f
        ]
        
        # Send to webapp if file exists
        if movement_files:
            latest_movement_file = max(
                [os.path.join('movement_scores', f) for f in movement_files], 
                key=os.path.getctime
            )
            
            send_haiku_to_webapp(
                latest_movement_file, 
                f"Midpoint Movement: {section.get('section_name', 'Unknown')} - {most_extreme_value}"
            )
        
        # Log the movement details
        with open(movement_log_path, 'a', encoding='utf-8') as log:
            log.write(json.dumps(movement_details, indent=2) + "\n\n")
        
        # Subtle modification of cultural memory to create organic evolution
        for value in ashari.cultural_memory:
            import random
            fluctuation = random.uniform(-0.02, 0.02)
            ashari.cultural_memory[value] += fluctuation
            # Ensure values stay within -1 to 1 range
            ashari.cultural_memory[value] = max(-1, min(1, ashari.cultural_memory[value]))
        
        # Save the updated Ashari state
        ashari.save_state()
        
        print(f"🌀 Generated midpoint movement for {section.get('section_name', 'Unknown')}")
        print(f"   Extreme Value: {most_extreme_value} (Score: {extreme_value_score:.2f})")
        print(f"   Movement: {movement_score}")
        
        return movement_details
    
    except Exception as e:
        print(f"❌ Error generating midpoint movement: {e}")
        return None

def setup_section_midpoint_monitors(performance_model, score_manager):
    """
    Set up monitors for section midpoint movements.
    
    Args:
        performance_model (dict): Performance model from score manager
        score_manager (AshariScoreManager): Score manager instance
    
    Returns:
        list: Midpoint movement monitor configurations
    """
    midpoint_monitors = []
    
    # Access the Ashari instance from the score manager
    ashari = score_manager.ashari
    
    for section in performance_model.get('sections', []):
        # Ensure the section has a midpoint time
        if 'midpoint_seconds' not in section:
            print(f"⚠️ No midpoint for section {section.get('section_name', 'Unknown')}")
            continue
        
        midpoint_seconds = section['midpoint_seconds']
        
        def create_midpoint_movement_callback(section_data):
            """
            Create a callback for generating movement at section midpoint.
            
            Args:
                section_data (dict): Section data for this specific callback
            
            Returns:
                function: Callback to generate movement
            """
            def midpoint_movement_callback(current_time_seconds):
                """
                Actual callback to generate movement at midpoint.
                
                Args:
                    current_time_seconds (float): Current performance time
                """
                return generate_midpoint_movement(ashari, section_data, current_time_seconds)
            
            return midpoint_movement_callback
        
        # Create and store the midpoint monitor configuration
        midpoint_monitors.append({
            'time': midpoint_seconds,
            'callback': create_midpoint_movement_callback(section)
        })
    
    return midpoint_monitors

# Optional: Direct usage for testing or standalone execution
if __name__ == "__main__":
    from ashari import Ashari
    
    # Load performance model
    with open('performance_model.json', 'r') as f:
        performance_model = json.load(f)
    
    # Initialize Ashari
    ashari = Ashari()
    ashari.load_state()
    
    # Setup monitors (would typically be done in main performance script)
    midpoint_monitors = setup_section_midpoint_monitors(performance_model, ashari)
    
    print("Midpoint Monitors Configured:")
    for monitor in midpoint_monitors:
        print(f"  - At {monitor['time']} seconds")