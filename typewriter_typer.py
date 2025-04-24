import serial
from pynput.keyboard import Controller
import time

# Adjust to match your Arduino port
SERIAL_PORT = '/dev/tty.usbmodem14201'
BAUD_RATE = 9600

# Setup serial connection and keyboard control
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
keyboard = Controller()

print(f"[Typewriter] Listening on {SERIAL_PORT}...")

while True:
    if ser.in_waiting > 0:
        char = ser.read().decode('utf-8')
        if char in ['\n', '\r']:
            continue  # Skip newline characters

        keyboard.press(char)
        keyboard.release(char)
        print(f"{char}", end="", flush=True)  # Print live text like a typewriter

        time.sleep(0.02)  # Small delay to ensure clean keypress
