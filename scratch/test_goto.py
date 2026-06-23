#!/usr/bin/env python3
import serial
import time

PORT = "/dev/ttyACM0"
BAUD = 9600

def send_cmd(ser, cmd, wait_reply=True):
    print(f"--> Sending: {cmd}")
    ser.write(cmd.encode('ascii'))
    if wait_reply:
        reply = ser.read_until(b"#")
        reply_str = reply.decode('ascii').rstrip('#')
        print(f"<-- Reply: {reply_str}")
        return reply_str
    return ""

def main():
    print(f"Connecting to Arduino Mega on {PORT} at {BAUD} baud...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1.0)
    except Exception as e:
        print(f"Error opening port: {e}")
        return

    # Wait for Arduino bootloader / reboot
    time.sleep(3.0)
    ser.reset_input_buffer()

    print("\n--- 1. Set Date, Time and Site Coordinates ---")
    send_cmd(ser, ":SC06/08/26#") # Date
    send_cmd(ser, ":SL10:15:44#") # Time
    send_cmd(ser, ":SG-02#")      # UTC Offset (+2h)
    send_cmd(ser, ":St+43*58:10#") # Latitude
    send_cmd(ser, ":Sg+006*22:31#") # Longitude

    print("\n--- 2. Set Mount to German Equatorial (mountType = 2) ---")
    send_cmd(ser, ":BMg#")

    print("\n--- 3. Query Current Position ---")
    current_ra = send_cmd(ser, ":GR#")
    current_dec = send_cmd(ser, ":GD#")
    print(f"Start Position: RA={current_ra}, DEC={current_dec}")

    # Query Pier Side
    pier_side = send_cmd(ser, ":Gm#")
    print(f"Start Pier Side: {pier_side}")

    print("\n--- 4. Set Target Coordinates ---")
    # Set target far from current position to watch the movement
    send_cmd(ser, ":Sr15:30:00#")
    send_cmd(ser, ":Sd+45*00:00#")

    print("\n--- 5. Trigger GoTo Slew (:MS#) ---")
    slew_started = send_cmd(ser, ":MS#")
    if slew_started == "0":
        print("GoTo Slew started successfully!")
    else:
        print(f"Failed to start slew. Error: {slew_started}")
        ser.close()
        return

    print("\n--- 6. Monitoring GoTo Progress ---")
    # Poll positions to see movement
    for _ in range(15):
        time.sleep(1.0)
        ra = send_cmd(ser, ":GR#")
        dec = send_cmd(ser, ":GD#")
        pier = send_cmd(ser, ":Gm#")
        # Query if slewing (via GBE status)
        gbe = send_cmd(ser, ":GBE#")
        print(f"Live: RA={ra} | DEC={dec} | Pier={pier} | GBE={gbe}")
        # GBE format: tracking,slewing,limitHit,maxRate*10,alt,az,parked,aligned
        # If slewing is 0 (the second field), GoTo is complete
        fields = gbe.split(',')
        if len(fields) >= 2 and fields[1] == '0':
            print("GoTo reached target destination!")
            break

    print("\n--- 7. Stop Slew / Cleanup ---")
    send_cmd(ser, ":Q#", wait_reply=False)
    ser.close()
    print("Test complete.")

if __name__ == "__main__":
    main()
