#!/usr/bin/env python3
import serial
import time
import sys

PORT = "/dev/ttyACM0"
BAUD = 38400

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
    print(f"Connecting to real Arduino Mega on {PORT} at {BAUD} baud...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1.5)
    except Exception as e:
        print(f"Error opening port: {e}")
        print("Please check if the Arduino is connected and you have permissions (sudo chmod 666 /dev/ttyACM0).")
        sys.exit(1)

    # Wait for Arduino bootloader to finish
    print("Waiting 3 seconds for Arduino reboot...")
    time.sleep(3.0)
    ser.reset_input_buffer()

    print("\n--- 1. Query Firmware Version ---")
    ver = send_cmd(ser, ":GVP#")
    if not ver:
        print("Error: No reply from Arduino. Check wiring or baudrate.")
        ser.close()
        sys.exit(1)

    print("\n--- 2. Initialize Date and Time (Required for GOTO) ---")
    # Mega requires Date and Time to set its internal clock and enable GOTO
    send_cmd(ser, ":SC14/06/26#") # Date (DD/MM/YY)
    send_cmd(ser, ":SL11:10:00#") # Time (HH:MM:SS)
    send_cmd(ser, ":SG-02#")      # UTC Offset
    
    print("\n--- 3. Query Start Position ---")
    current_ra = send_cmd(ser, ":GR#")
    current_dec = send_cmd(ser, ":GD#")
    print(f"Start Position: RA={current_ra}, DEC={current_dec}")

    print("\n--- 4. Set Target Coordinates ---")
    # Target: 12h 30m 00s, +45d 00' 00"
    send_cmd(ser, ":Sr12:30:00#")
    send_cmd(ser, ":Sd+45*00:00#")

    print("\n--- 5. Trigger GoTo Slew (:MS#) ---")
    slew_started = send_cmd(ser, ":MS#")
    if slew_started == "0":
        print("GoTo Slew started successfully!")
    else:
        print(f"Failed to start slew or slew rejected by Mega. Return value: {slew_started}")
        print("Note: If '1' is returned, target is below horizon or mount has cable limit hit.")
        ser.close()
        sys.exit(1)

    print("\n--- 6. Monitoring GoTo Progress ---")
    for i in range(10):
        time.sleep(0.8)
        ra = send_cmd(ser, ":GR#")
        dec = send_cmd(ser, ":GD#")
        print(f"Slewing position {i}: RA={ra} | DEC={dec}")
        
    print("\n--- 7. Stopping Slew (:Q#) ---")
    send_cmd(ser, ":Q#", wait_reply=False)
    print("Slew stopped.")
    
    ser.close()
    print("\n*** TEST OF REAL ARDUINO COMPLETE ***")

if __name__ == "__main__":
    main()
