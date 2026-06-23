#!/usr/bin/env python3
import serial
import time
import sys

def activate_tracking():
    port = "/dev/ttyACM0"
    baud = 38400
    print(f"Connecting to Arduino on {port} at {baud} baud...")
    
    try:
        ser = serial.Serial(port, baud, timeout=1.5)
        # Wait for reboot
        time.sleep(2.0)
        ser.reset_input_buffer()
        
        # Check connection with handshake (retry up to 3 times)
        resp = ""
        for attempt in range(3):
            ser.write(b":GVP#")
            resp = ser.read_until(b"#").decode('ascii', errors='ignore')
            print(f"Handshake attempt {attempt+1}: received {repr(resp)}")
            if "OnStep" in resp:
                break
            time.sleep(0.5)
            
        if "OnStep" not in resp:
            print("Error: Arduino did not respond correctly to handshake.")
            ser.close()
            sys.exit(1)
        print("Connected to Arduino successfully.")
        
        # Get status before
        ser.write(b":GBE#")
        status_before = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        print(f"Status before: {status_before}")
        parts_before = status_before.split(',')
        is_tracking_before = parts_before[0] == '1' if len(parts_before) > 0 else False
        print(f"  Tracking active: {is_tracking_before}")
        
        # Activate tracking
        print("Sending tracking activation command (:Te#)...")
        ser.write(b":Te#")
        reply = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"  Arduino reply: {repr(reply)}")
        
        # Get status after
        ser.write(b":GBE#")
        status_after = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        print(f"Status after: {status_after}")
        parts_after = status_after.split(',')
        is_tracking_after = parts_after[0] == '1' if len(parts_after) > 0 else False
        print(f"  Tracking active: {is_tracking_after}")
        
        if is_tracking_after:
            print("Tracking successfully ACTIVATED!")
            # Trigger confirmation beep
            ser.write(b":Bbp#")
            ser.read_until(b"#")
        else:
            print("Failed to activate tracking.")
            
        ser.close()
    except Exception as e:
        print(f"Error communicating with Arduino: {e}")
        sys.exit(1)

if __name__ == "__main__":
    activate_tracking()
