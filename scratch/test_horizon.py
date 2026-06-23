#!/usr/bin/env python3
import serial
import time
import sys

def test_horizon_limit():
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
        
        # Unpark if parked
        ser.write(b":hQ#")
        park_status = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        if park_status == '1':
            print("Mount is parked. Sending unpark command (:hR#)...")
            ser.write(b":hR#")
            ser.read_until(b"#")
            time.sleep(1.0)
            
        # 1. Test AltAz Below Horizon Slew Command (:MA#)
        # Target Alt: -5.0 degrees, Target Az: 180.0 degrees
        target_alt = -5.0
        target_az = 180.0
        
        # Set target Azimuth (Meade :Sz command)
        print(f"\nSetting target Azimuth to {target_az}° (:Sz180*00:00#)...")
        ser.write(b":Sz180*00:00#")
        reply_az = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"  Response: {repr(reply_az)} (should be '1')")
        
        # Set target Altitude below horizon (Meade :Sa command)
        print(f"Setting target Altitude to {target_alt}° (:Sa-05*00:00#) -> Below Horizon limit of -1.0°...")
        ser.write(b":Sa-05*00:00#")
        reply_alt = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"  Response: {repr(reply_alt)} (should be '1')")
        
        # Trigger Slew (Meade :MA command)
        print("Sending Slew command (:MA#)...")
        ser.write(b":MA#")
        reply_slew = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"  Slew Response: {repr(reply_slew)}")
        
        # Check if it was rejected with the correct message
        if "Below horizon" in reply_slew:
            print("\nSUCCESS: The slew command was correctly REJECTED by the firmware with a 'Below horizon' safety alarm!")
            
            # Check GBE telemetry to make sure it's not moving and limitHit is true
            ser.write(b":GBE#")
            telemetry = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
            print(f"Telemetry (:GBE#): {telemetry}")
            parts = telemetry.split(',')
            if len(parts) >= 8:
                print(f"  Slewing state: {parts[1]} (should be 0)")
                print(f"  Limit hit:    {parts[2]} (should be 1)")
                
            # Trigger warning beep to signal the error condition
            print("\nPlaying safety warning beep on mount buzzer...")
            ser.write(b":Bbp#")
            ser.read_until(b"#")
        else:
            print("\nFAILURE: Slew was not rejected as expected.")
            
        ser.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_horizon_limit()
