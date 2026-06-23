import serial
import time

def send_cmd(ser, cmd, desc):
    print(f"Testing {cmd.strip().decode()} ({desc})...", end=" ")
    ser.write(cmd)
    try:
        resp = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"Response: {resp}")
    except Exception as e:
        print(f"Error reading: {e}")

def test():
    try:
        print("Connecting to /dev/ttyACM0 at 9600 baud...")
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1.5)
        time.sleep(2.0)
        ser.reset_input_buffer()
        
        commands = [
            (b":GVP#", "Product Name"),
            (b":GVN#", "Firmware Version"),
            (b":GR#", "Get Right Ascension"),
            (b":GD#", "Get Declination"),
            (b":GA#", "Get Altitude"),
            (b":GZ#", "Get Azimuth"),
            (b":GL#", "Get Local Time"),
            (b":GC#", "Get Date"),
            (b":Gt#", "Get Latitude"),
            (b":Gg#", "Get Longitude"),
            (b":GW#", "Get Alignment/Mount Status"),
            (b":GU#", "Global Status"),
            (b":GBE#", "GotoUniversal Extended Status")
        ]
        
        for cmd, desc in commands:
            send_cmd(ser, cmd, desc)
            time.sleep(0.1)

        ser.close()
        print("\nAll read tests completed.")
    except Exception as e:
        print(f"Serial Error: {e}")

if __name__ == '__main__':
    test()
