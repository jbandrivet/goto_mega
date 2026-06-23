#!/usr/bin/env python3
import serial
import time
import sys

def test_parking():
    port = "/dev/ttyACM0"
    baud = 38400
    print(f"Connecting to Arduino on {port} at {baud} baud...")
    
    try:
        ser = serial.Serial(port, baud, timeout=1.5)
        # Wait for reboot
        time.sleep(2.0)
        ser.reset_input_buffer()
        
        # Handshake
        resp = ""
        for attempt in range(3):
            ser.write(b":GVP#")
            resp = ser.read_until(b"#").decode('ascii', errors='ignore')
            if "OnStep" in resp:
                break
            time.sleep(0.5)
            
        if "OnStep" not in resp:
            print("Error: Handshake failed.")
            ser.close()
            sys.exit(1)
        print("Handshake success. Connected to OnStep device.")
        
        # Check current park status
        ser.write(b":hQ#")
        park_status = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        print(f"Current Park status (from :hQ#): {repr(park_status)} (1 = parked, 0 = active)")
        
        if park_status == '1':
            print("Mount is currently PARKED. Sending unpark command (:hR#) to prepare for test...")
            ser.write(b":hR#")
            unpark_reply = ser.read_until(b"#").decode('ascii', errors='ignore')
            print(f"  Unpark reply: {repr(unpark_reply)}")
            time.sleep(1.0)
            
            # Check status again
            ser.write(b":hQ#")
            park_status = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
            print(f"  Park status after unparking: {repr(park_status)}")
            
        print("\nSending park command (:hP#)...")
        ser.write(b":hP#")
        park_reply = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"  Immediate park response (should be '1'): {repr(park_reply)}")
        
        # Poll the park status until it becomes 1
        print("Polling park status (please wait while mount slews to park position)...")
        start_time = time.time()
        is_parked = False
        
        for _ in range(60): # timeout after 30 seconds (60 * 0.5s)
            ser.write(b":hQ#")
            status = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
            elapsed = time.time() - start_time
            print(f"  Elapsed: {elapsed:.1f}s | Park status: {repr(status)}")
            if status == '1':
                is_parked = True
                break
            time.sleep(0.5)
            
        if is_parked:
            print(f"\nMount successfully PARKED in {time.time() - start_time:.1f} seconds!")
            
            # Query GBE telemetry
            ser.write(b":GBE#")
            telemetry = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
            print(f"Telemetry (:GBE#): {telemetry}")
            parts = telemetry.split(',')
            
            # Format: tracking,slewing,limitHit,maxRate*10,alt,az,parked,aligned
            if len(parts) >= 8:
                print(f"  Tracking:   {parts[0]} (should be 0)")
                print(f"  Slewing:    {parts[1]} (should be 0)")
                print(f"  Alt Coord:  {parts[4]}°")
                print(f"  Az Coord:   {parts[5]}°")
                print(f"  Parked Flag:{parts[6]} (should be 1)")
            
            # Play a double beep to confirm park is done and motors are disabled
            print("\nPlaying double beep on mount buzzer to signal parking complete...")
            ser.write(b":Bbp#")
            ser.read_until(b"#")
            time.sleep(0.2)
            ser.write(b":Bbp#")
            ser.read_until(b"#")
            print("Double beep sent. Motors should now be soft/free.")
        else:
            print("\nError: Mount parking timed out or failed.")
            
        ser.close()
    except Exception as e:
        print(f"Error during communication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_parking()
