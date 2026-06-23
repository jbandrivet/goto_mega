import serial
import time

def test_config(ser, mode_name, cmd):
    print(f"\n--- Testing Configuration: {mode_name} ---")
    print(f"Sending config command {cmd}...")
    ser.write(cmd)
    time.sleep(1) # wait for eeprom write and apply
    
    ser.reset_input_buffer()
    print("Sending :GW# to verify mount type...")
    ser.write(b":GW#")
    resp = ser.read_until(b"#").decode('ascii', errors='ignore')
    print(f"Response to :GW#: {resp}")
    if len(resp) >= 3:
        mount_char = resp[0]
        mount_str = {'A': 'AltAz', 'P': 'ForkEq', 'G': 'GermanEq'}.get(mount_char, 'Unknown')
        print(f"-> Verified Mount Type: {mount_str} (code '{mount_char}')")

def test():
    try:
        print("Connecting to /dev/ttyACM0 at 9600 baud...")
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1.5)
        time.sleep(2.0)
        ser.reset_input_buffer()
        
        # 1. Alt Az
        test_config(ser, "Universal - Alt-Azimutale", b":BMa#")
        
        # 2. Fork Eq
        test_config(ser, "Universal - Fourche Equatoriale", b":BMe#")
        
        # 3. German Eq
        test_config(ser, "Universal - Monture Equatoriale Allemande", b":BMg#")
        
        ser.close()
        print("\nAll Universal configuration tests completed.")
    except Exception as e:
        print(f"Serial Error: {e}")

if __name__ == '__main__':
    test()
