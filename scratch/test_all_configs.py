import serial
import time

def run_tests_for_config(ser, mode_name, config_cmd, expected_char):
    print(f"\n==================================================")
    print(f" TESTING CONFIGURATION: {mode_name} (Expected: '{expected_char}')")
    print(f"==================================================")
    
    # 1. Set the configuration
    print(f"Sending config command: {config_cmd.decode()}")
    ser.write(config_cmd)
    time.sleep(1.0) # Allow EEPROM write
    ser.reset_input_buffer()
    
    # 2. Check idle state status commands
    print("\n--- Testing Idle State ---")
    ser.write(b":GW#")
    gw_resp = ser.read_until(b"#").decode('ascii', errors='ignore')
    print(f"Idle :GW# response: {gw_resp}")
    
    ser.write(b"\x06")
    ack_resp = ser.read(1).decode('ascii', errors='ignore')
    print(f"Idle ACK (6) response: {ack_resp}")

    ser.write(b":A?#")
    a_query_resp = ser.read_until(b"#").decode('ascii', errors='ignore')
    print(f"Idle :A?# response: {a_query_resp}")
    
    if len(gw_resp) > 0 and gw_resp[0] == expected_char:
        print("✔ Idle :GW# test PASSED")
    else:
        print("✘ Idle :GW# test FAILED")
        
    if ack_resp == expected_char:
        print("✔ Idle ACK test PASSED")
    else:
        print("✘ Idle ACK test FAILED")

    if a_query_resp == "300#":
        print("✔ Idle :A?# test PASSED")
    else:
        print("✘ Idle :A?# test FAILED")

    # 3. Prepare target and start GOTO (slew)
    print("\n--- Starting Slew/GOTO ---")
    
    # Set Alt target to +45*00:00
    ser.write(b":Sa+45*00:00#")
    ser.read_until(b"#") # Consume the response
    
    # Set Az target to 180*00:00
    ser.write(b":Sz180*00:00#")
    ser.read_until(b"#") # Consume the response
    
    # Trigger Slew
    ser.write(b":MA#")
    ma_resp = ser.read(1).decode('ascii', errors='ignore')
    print(f"Slew trigger (:MA#) response: '{ma_resp}'")
    if ma_resp != '0':
        print(f"Warning: Slew did not start successfully. Response was: {ma_resp}")
        # If it failed because it's below horizon or similar, let's try another angle
        # Let's try Alt = 10 degrees
        ser.write(b":Sa+10*00:00#")
        ser.read_until(b"#")
        ser.write(b":MA#")
        ma_resp = ser.read(1).decode('ascii', errors='ignore')
        print(f"Retrying slew trigger (:MA#) response: '{ma_resp}'")
        
    time.sleep(0.5) # Let the slew settle into the loop
    
    # 4. Check status commands DURING GOTO (slew)
    print("\n--- Testing Slew State ---")
    ser.write(b":GW#")
    slew_gw_resp = ser.read_until(b"#").decode('ascii', errors='ignore')
    print(f"Slew :GW# response: {slew_gw_resp}")
    
    ser.write(b"\x06")
    slew_ack_resp = ser.read(1).decode('ascii', errors='ignore')
    print(f"Slew ACK (6) response: {slew_ack_resp}")

    ser.write(b":A?#")
    slew_a_query_resp = ser.read_until(b"#").decode('ascii', errors='ignore')
    print(f"Slew :A?# response: {slew_a_query_resp}")
    
    if len(slew_gw_resp) > 0 and slew_gw_resp[0] == expected_char:
        print("✔ Slew :GW# test PASSED")
    else:
        print("✘ Slew :GW# test FAILED")
        
    if slew_ack_resp == expected_char:
        print("✔ Slew ACK test PASSED")
    else:
        print("✘ Slew ACK test FAILED")

    if slew_a_query_resp == "300#":
        print("✔ Slew :A?# test PASSED")
    else:
        print("✘ Slew :A?# test FAILED")
        
    # 5. Stop the GOTO (abort slew)
    print("\nAborting slew (:Q#)...")
    ser.write(b":Q#")
    time.sleep(1.0)
    ser.reset_input_buffer()
    print("Slew stopped.")

def main():
    try:
        print("Connecting to /dev/ttyACM0 at 9600 baud...")
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2.0)
        time.sleep(2.0) # Wait for Arduino reset
        ser.reset_input_buffer()
        
        # Test AltAz (A)
        run_tests_for_config(ser, "Alt-Azimuthal (Dobson)", b":BMa#", 'A')
        
        # Test ForkEq (P)
        run_tests_for_config(ser, "Fork Equatorial", b":BMe#", 'P')
        
        # Test GermanEq (G)
        run_tests_for_config(ser, "German Equatorial", b":BMg#", 'G')
        
        ser.close()
        print("\n==================================================")
        print("ALL TESTS COMPLETED!")
        print("==================================================")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
