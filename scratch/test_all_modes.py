#!/usr/bin/env python3
import serial
import time

PORT = "/dev/ttyACM0"
BAUD = 9600

def send_cmd(ser, cmd, wait_reply=True):
    ser.write(cmd.encode('ascii'))
    if wait_reply:
        reply = ser.read_until(b"#")
        reply_str = reply.decode('ascii').rstrip('#')
        return reply_str
    return ""

def test_mode(ser, mode_name, init_cmd):
    print(f"\n==========================================")
    print(f" TESTING MODE: {mode_name}")
    print(f"==========================================")
    
    # 1. Set Mount Mode
    reply = send_cmd(ser, f":{init_cmd}#")
    print(f"Set Mode command (:{init_cmd}#) -> Reply: {reply}")
    
    # 2. Verify Mount Name
    mount_name = send_cmd(ser, ":GM#")
    print(f"Query Mount Name (:GM#) -> Reply: {mount_name}")
    
    # 3. Verify Pier Side Behavior
    pier_side = send_cmd(ser, ":Gm#")
    print(f"Query Pier Side (:Gm#) -> Reply: {pier_side}")
    
    # 4. Trigger GoTo Slew to a safe target
    # Set safe targets
    send_cmd(ser, ":Sr12:00:00#")
    send_cmd(ser, ":Sd+30*00:00#")
    slew_reply = send_cmd(ser, ":MS#")
    print(f"Start Slew (:MS#) -> Reply: {slew_reply}")
    
    if slew_reply == "0":
        print("GoTo Slew started successfully. Monitoring for 3 seconds...")
        for i in range(3):
            time.sleep(1.0)
            ra = send_cmd(ser, ":GR#")
            dec = send_cmd(ser, ":GD#")
            pier = send_cmd(ser, ":Gm#")
            gbe = send_cmd(ser, ":GBE#")
            print(f"  [{i+1}s] RA={ra} | DEC={dec} | Pier={pier} | GBE={gbe}")
        # Stop slew
        send_cmd(ser, ":Q#", wait_reply=False)
        print("Slew stopped.")
    else:
        print(f"GoTo Slew failed to start. Reply code: {slew_reply}")

def main():
    print(f"Connecting to Arduino Mega on {PORT}...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1.0)
    except Exception as e:
        print(f"Error: {e}")
        return

    time.sleep(3.0)
    ser.reset_input_buffer()

    # Sync time/date/coords so GoTo works
    send_cmd(ser, ":SC06/08/26#")
    send_cmd(ser, ":SL10:20:00#")
    send_cmd(ser, ":SG-02#")
    send_cmd(ser, ":St+43*58:10#")
    send_cmd(ser, ":Sg+006*22:31#")

    # TEST 1: AltAz
    test_mode(ser, "Alt-Azimuth (AltAz)", "BMa")
    
    # Verify horizon limit on AltAz (Should refuse GoTo below horizon)
    print("\nChecking Horizon Limit on AltAz...")
    send_cmd(ser, ":Sr12:00:00#")
    send_cmd(ser, ":Sd-50*00:00#") # This target is well below horizon at this time/lat
    limit_reply = send_cmd(ser, ":MS#")
    print(f"Slew below horizon (:MS#) -> Reply: {limit_reply} (Expected: '1Below horizon' or error code)")

    # TEST 2: Fork Equatorial
    test_mode(ser, "Fork Equatorial (ForkEq)", "BMe")

    # TEST 3: German Equatorial
    test_mode(ser, "German Equatorial (GermanEq)", "BMg")

    ser.close()
    print("\nAll tests complete.")

if __name__ == "__main__":
    main()
