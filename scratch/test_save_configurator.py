#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
import goto_mega_config_tool as config_tool

def test_saving_configuration():
    port = "/dev/ttyACM0"
    baud = 38400
    print(f"Connecting to Arduino on {port} at {baud} baud for saving test...")
    
    app = config_tool.ConfigToolApp()
    
    # Establish serial link
    import serial
    try:
        app.ser = serial.Serial(port, baud, timeout=1.5)
        time.sleep(2.0)
        app.ser.reset_input_buffer()
        
        # Handshake
        app.ser.write(b":GVP#")
        resp = app.ser.read_until(b"#").decode('ascii', errors='ignore')
        if "OnStep" not in resp:
            print("Handshake failed.")
            app.ser.close()
            sys.exit(1)
        app.is_connected = True
        app.update_connection_status()
        print("Connected successfully.")
        
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)
        
    try:
        # 1. Read existing configuration first
        print("\nReading active configuration...")
        app.ser.write(b":BRa#")
        initial_rev_az = app.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#') == '1'
        print(f"  Current AZ direction inversion: {initial_rev_az}")
        
        # 2. Toggle the direction inversion setting to test the write
        new_rev_az = not initial_rev_az
        print(f"\nWriting new configuration setting:")
        print(f"  Target AZ direction inversion: {new_rev_az}")
        
        # Populate the GUI fields with test configuration
        app.mount_type_var.set("AltAz")
        app.steps_entry.delete(0, config_tool.tk.END)
        app.steps_entry.insert(0, "200")
        app.microstep_var.set("125")
        app.gear_az_entry.delete(0, config_tool.tk.END)
        app.gear_az_entry.insert(0, "750.0")
        app.gear_alt_entry.delete(0, config_tool.tk.END)
        app.gear_alt_entry.insert(0, "750.0")
        app.lat_entry.delete(0, config_tool.tk.END)
        app.lat_entry.insert(0, "43.9694")
        app.lon_entry.delete(0, config_tool.tk.END)
        app.lon_entry.insert(0, "6.3753")
        app.speed_scale.set(2.0)
        app.buzzer_var.set(True)
        
        # Set the target inversion checkboxes
        app.rev_az_var.set(new_rev_az)
        app.rev_alt_var.set(True) # Turn Alt inversion ON
        
        # Run apply configuration
        print("Executing Apply & Save configuration...")
        app.apply_config_to_arduino()
        
        # 3. Read back the configuration to verify it was stored in EEPROM
        print("\nReading back the parameters to verify storage...")
        app.ser.write(b":BRa#")
        read_rev_az = app.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#') == '1'
        app.ser.write(b":BRe#")
        read_rev_alt = app.ser.read_until(b"#").decode('ascii', errors='ignore').strip('#') == '1'
        
        print(f"  Verified AZ direction inversion: {read_rev_az}")
        print(f"  Verified ALT direction inversion: {read_rev_alt}")
        
        if read_rev_az == new_rev_az and read_rev_alt == True:
            print("\nSUCCESS: Parameters were successfully written, saved to EEPROM, and verified!")
        else:
            print("\nFAILURE: Parameters did not match.")
            sys.exit(1)
            
        # Revert the test setting back to the initial value for cleanliness
        print("\nCleaning up (reverting AZ inversion to original state)...")
        app.rev_az_var.set(initial_rev_az)
        app.apply_config_to_arduino()
        
        app.ser.close()
        app.destroy()
        print("Saving test completed successfully.")
        
    except Exception as e:
        print(f"Error during saving check: {e}")
        app.ser.close()
        sys.exit(1)

if __name__ == "__main__":
    # Mock showinfo/showerror to prevent GUI popups blocking test
    from unittest.mock import patch
    with patch("tkinter.messagebox.showinfo"), patch("tkinter.messagebox.showerror"):
        test_saving_configuration()
