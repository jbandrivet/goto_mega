import serial
import time

def test():
    try:
        print("Connecting to /dev/ttyACM0 at 9600 baud...")
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1.5)
        time.sleep(2.0)
        ser.reset_input_buffer()
        print("Sending :GW# to check align/mount status...")
        ser.write(b":GW#")
        resp = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"Response: {resp}")
        
        # Test also what mount type is in EEPROM if possible or just print the character
        if len(resp) >= 3:
            mount_char = resp[0]
            track_char = resp[1]
            align_char = resp[2]
            
            mount_str = {'A': 'AltAz', 'P': 'ForkEq', 'G': 'GermanEq'}.get(mount_char, 'Unknown')
            track_str = "Tracking" if track_char == 'T' else "Not Tracking"
            align_str = "Synced" if align_char == '1' else "Not Synced"
            
            print(f"Decoded -> Mount: {mount_str}, {track_str}, {align_str}")
            
        ser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test()
