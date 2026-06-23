import serial
import time
import sys

def send_cmd(ser, cmd, delay=0.1):
    ser.write(cmd.encode('ascii'))
    time.sleep(delay)
    resp = b""
    while ser.in_waiting > 0:
        resp += ser.read(1)
        time.sleep(0.005)
    res_str = resp.decode('ascii', errors='ignore').strip()
    print(f"  Send: {cmd.strip()} -> Received: '{res_str}'")
    return res_str

def monitor_slew(ser, duration=5.0):
    start = time.time()
    while time.time() - start < duration:
        status = send_cmd(ser, ":GBE#", delay=0.05)
        alt = send_cmd(ser, ":GA#", delay=0.05)
        az = send_cmd(ser, ":GZ#", delay=0.05)
        print(f"    Elapsed: {time.time() - start:.1f}s | GBE: {status} | Alt: {alt} | Az: {az}")
        time.sleep(0.8)

def test_mode(ser, mode_name, mode_cmd, expected_char):
    print(f"\n=========================================")
    print(f" TESTING MODE: {mode_name}")
    print(f"=========================================")
    
    # 1. Change mount type
    send_cmd(ser, f":{mode_cmd}#")
    
    # Verify mount type via global status
    gu = send_cmd(ser, ":GU#")
    # GU format: [n/N][p/P][H][S][G][F]/[A/P/G][o/e/w][rate]
    # Mount type char is at index 6 or 7 depending on flags. Let's check if expected_char is in GU.
    if expected_char in gu:
        print(f"  [OK] Mount type successfully changed to {mode_name} ('{expected_char}' found in GU)")
    else:
        print(f"  [WARNING] Mount type char '{expected_char}' not found in GU: '{gu}'")
        
    # 2. Sync site parameters
    send_cmd(ser, ":SG+01.0#")      # UTC+1
    send_cmd(ser, ":SL12:00:00#")   # Time
    send_cmd(ser, ":SC06/13/26#")   # Date
    send_cmd(ser, ":St+43*58:48#")  # Lat
    send_cmd(ser, ":Sg+006*01:12#") # Lon
    
    # 3. Unpark
    send_cmd(ser, ":hR#")
    
    # 4. Enable Tracking
    send_cmd(ser, ":Te#")
    gbe_track = send_cmd(ser, ":GBE#")
    if gbe_track.startswith("1"):
        print("  [OK] Tracking active (GBE starts with 1)")
    else:
        print(f"  [WARNING] Tracking might not be active: GBE='{gbe_track}'")

    # 5. Sync coordinates (current position to sky)
    lst_str = send_cmd(ser, ":GS#")
    # Parse LST
    parts = lst_str.strip('#').split(':')
    if len(parts) >= 2:
        h = int(parts[0])
        m = int(parts[1])
        # Define target coordinates (slew 10 degrees away in RA/Az to test movement)
        target_m = (m - 40) % 60
        target_h = h if target_m < m else (h - 1) % 24
        target_ra = f"{target_h:02d}:{target_m:02d}:00"
        
        print(f"  Syncing to LST RA={lst_str} DEC=+45*00:00...")
        send_cmd(ser, f":Sr{lst_str}#")
        send_cmd(ser, ":Sd+45*00:00#")
        send_cmd(ser, ":CM#") # Sync
        
        print(f"  Slewing to target RA={target_ra} DEC=+45*00:00...")
        send_cmd(ser, f":Sr{target_ra}#")
        send_cmd(ser, ":Sd+45*00:00#")
        
        # Trigger Slew
        res = send_cmd(ser, ":MS#")
        if res == "0":
            print("  [OK] Slew initiated!")
            # Monitor slew for a few seconds
            monitor_slew(ser, duration=4.0)
            # Stop slew
            send_cmd(ser, ":Q#")
            print("  [OK] Slew stopped manually.")
        else:
            print(f"  [ERROR] Slew rejected with code: '{res}'")
    else:
        print("  [ERROR] Could not read LST")

    # 6. Park
    print("  Parking mount...")
    send_cmd(ser, ":hP#")
    time.sleep(1.0)
    gbe_park = send_cmd(ser, ":GBE#")
    fields = gbe_park.split(',')
    # parked is field index 6 (7th element)
    if len(fields) >= 7 and fields[6] == '1':
         print("  [OK] Mount parked successfully (GBE parked field = 1)")
    else:
         print(f"  [WARNING] Mount might not be parked: GBE='{gbe_park}'")

def main():
    port = "/dev/ttyACM0"
    baud = 38400
    print(f"Connecting to {port} at {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1.0)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return
        
    # Reboot to start clean
    print("Rebooting Arduino...")
    ser.dtr = False
    time.sleep(0.2)
    ser.dtr = True
    time.sleep(3.0)
    ser.read(ser.in_waiting)
    
    # Save initial settings to restore later
    initial_mt = send_cmd(ser, ":GW#")
    print(f"Initial Mount Type: {initial_mt}")
    
    try:
        # Test 1: AltAz mode
        test_mode(ser, "AltAzimutale", "BMa", "A")
        
        # Test 2: ForkEq mode
        test_mode(ser, "Fourche Equatoriale", "BMe", "P")
        
        # Test 3: GermanEq mode
        test_mode(ser, "German Equatoriale", "BMg", "G")
        
        # Restore initial mount type
        print("\nRestoring initial mount type...")
        if "AltAz" in initial_mt or "AN1" in initial_mt:
            send_cmd(ser, ":BMa#")
        elif "Fork" in initial_mt:
            send_cmd(ser, ":BMe#")
        else:
            send_cmd(ser, ":BMg#")
            
        # Re-park to ensure it's clean
        send_cmd(ser, ":hP#")
        
    finally:
        ser.close()
        print("\nAll mount mode tests completed.")

if __name__ == '__main__':
    main()
