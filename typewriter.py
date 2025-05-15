import serial
import time
import glob
import queue
import threading

# Create a queue for storing keypresses
keypress_queue = queue.Queue()
typewriter_active = False  # Flag to control when typewriter input is processed

def find_arduino_port():
    """Find the serial port for the Arduino on macOS"""
    patterns = [
        '/dev/tty.usbmodem*',
        '/dev/tty.usbserial*'
    ]
    
    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    
    if ports:
        return ports[0]  # Return the first matching port
    else:
        return None

def initialize_typewriter():
    arduino_port = find_arduino_port()
    if not arduino_port:
        print("Arduino typewriter not found. Please check connection.")
        return None
    
    print(f"Connecting to Arduino typewriter on port: {arduino_port}")
    try:
        ser = serial.Serial(arduino_port, 9600, timeout=1)
        time.sleep(2)  # Give the connection time to establish
        print("Arduino typewriter connected successfully!")
        return ser
    except Exception as e:
        print(f"Error connecting to Arduino typewriter: {e}")
        return None

def read_from_typewriter_thread(ser):
    print("Typewriter reading thread started.")
    global typewriter_active
    
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                
                if line.startswith("Key pressed:"):
                    char = line.split(": ")[1]
                    
                    if typewriter_active:
                        print(f"Key: {char}")  # Simple debug output
                        keypress_queue.put(char)
                    else:
                        print(f"(Inactive: {char})")
        except Exception as e:
            print(f"Error reading from typewriter: {e}")
            break

def start_typewriter_reader():
    ser = initialize_typewriter()
    if ser:
        thread = threading.Thread(target=read_from_typewriter_thread, args=(ser,), daemon=True)
        thread.start()
        return True
    return False

def activate_typewriter():
    global typewriter_active
    typewriter_active = True
    print("Typewriter activated!")
    clear_queue()  # Clear any pending keypresses

def deactivate_typewriter():
    global typewriter_active
    typewriter_active = False
    print("Typewriter deactivated.")

def clear_queue():
    """Clear all pending keypresses from the queue"""
    while not keypress_queue.empty():
        keypress_queue.get_nowait()

def get_next_key(timeout=0.1):
    """Get the next key press from the typewriter, non-blocking"""
    try:
        return keypress_queue.get(timeout=timeout)
    except queue.Empty:
        return None

def get_typewriter_input():
    """Collect characters until 'p' is pressed, then return the collected input"""
    print("\nWaiting for typewriter input. Press 'p' to submit.")
    input_buffer = []
    collecting = True
    
    # Clear any existing characters in the queue
    clear_queue()
    
    while collecting:
        key = get_next_key(0.1)  # Check for keypresses every 0.1 seconds
        
        if key:
            if key == 'p':
                print("\nInput submitted!")
                collecting = False
            else:
                input_buffer.append(key)
                current_input = ''.join(input_buffer)
                print(f"\rCurrent input: {current_input}", end="", flush=True)
        
        # Short delay to prevent CPU hogging
        time.sleep(0.05)
    
    final_input = ''.join(input_buffer)
    print(f"\nFinal input: '{final_input}'")
    return final_input

# For testing
if __name__ == "__main__":
    print("Typewriter module test mode")
    if start_typewriter_reader():
        input("Press Enter to activate typewriter...")
        activate_typewriter()
        
        while True:
            user_input = get_typewriter_input()
            print(f"Collected input: '{user_input}'")
            
            if user_input == "exit":
                print("Exiting...")
                break