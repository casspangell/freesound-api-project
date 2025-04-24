# arduino_input.py
import serial
import threading
from queue import Queue

def start_arduino_listener(port='/dev/tty.usbmodem14201', baud=9600):
    input_queue = Queue()

    def read_serial():
        try:
            ser = serial.Serial(port, baud, timeout=1)
            buffer = ""
            while True:
                if ser.in_waiting > 0:
                    char = ser.read().decode('utf-8')
                    if char == '\r' or char == '\n':
                        if buffer:
                            input_queue.put(buffer)
                            buffer = ""
                    else:
                        buffer += char
        except serial.SerialException as e:
            print(f"[Arduino] Serial error: {e}")

    thread = threading.Thread(target=read_serial, daemon=True)
    thread.start()
    return input_queue
