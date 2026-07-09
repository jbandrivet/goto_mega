#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))
import goto_mega_config_tool as config_tool

def test_real_arduino_connection():
    print("Initializing Configurator App...")
    app = config_tool.ConfigToolApp()
    
    # Set target port and baud rate
    port = "/dev/ttyACM0"
    baud = 38400
    app.port_var.set(port)
    app.baud_var.set(str(baud))
    
    print(f"Attempting connection to Arduino on {port} at {baud} baud...")
    
    # Manually run the connection process without messagebox popups
    try:
        import serial
        app.ser = serial.Serial(port, baud, timeout=1.5)
        # Wait for Arduino bootloader reset
        time.sleep(2.0)
        app.ser.reset_input_buffer()
        
        # Check connection with handshake (retry up to 3 times)
        resp = ""
        for attempt in range(3):
            app.ser.write(b":GVP#")
            resp = app.ser.read_until(b"#").decode('ascii', errors='ignore')
            print(f"Handshake attempt {attempt+1}: received {repr(resp)}")
            if "OnStep" in resp:
                break
            time.sleep(0.5)
        
        if "OnStep" in resp:
            app.is_connected = True
            app.update_connection_status()
            print("Handshake SUCCESS. Connected to OnStep device.")
        else:
            app.ser.close()
            app.ser = None
            print("Handshake FAILED. Device did not respond to GVP command.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
        
    print("\nReading active configuration from the Arduino...")
    try:
        # Latitude
        app.ser.write(b":Gt#")
        lat_raw = app.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        print(f"Raw Latitude response: {repr(lat_raw)}")
        
        # Longitude
        app.ser.write(b":Gg#")
        lon_raw = app.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        print(f"Raw Longitude response: {repr(lon_raw)}")
        
        # Slew speed
        app.ser.write(b":Bv#")
        speed_raw = app.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        print(f"Raw Slew speed response: {repr(speed_raw)}")
        
        # Parse and display
        lat_val = app.parse_lx_coords(lat_raw)
        lon_val = app.parse_lx_coords(lon_raw)
        speed_val = int(speed_raw) / 10.0
        
        print("\nSuccessfully parsed values:")
        print(f"  Latitude:  {lat_val:.4f}° (expected around 43.9694°)")
        print(f"  Longitude: {lon_val:.4f}° (expected around 6.3753°)")
        print(f"  GoTo Speed:{speed_val:.1f} °/s (expected around 2.0 °/s)")
        
        # Test a quick beep
        print("\nTesting buzzer beep command on physical mount...")
        app.ser.write(b":Bbp#")
        app.ser.read_until(b"#")
        print("Beep command sent.")
        
    except Exception as e:
        print(f"Error during reading/parsing: {e}")
        app.ser.close()
        sys.exit(1)
        
    print("\nDisconnecting...")
    app.ser.close()
    app.destroy()
    print("Integration test COMPLETED successfully!")

if __name__ == "__main__":
    test_real_arduino_connection()
