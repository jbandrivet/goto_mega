import serial, sys, time

for port in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2", "/dev/ttyACM3"]:
    try:
        ser = serial.Serial(port, 38400, timeout=1)
        # Wait for reset
        time.sleep(2.5)
        ser.write(b":GR#")
        time.sleep(0.2)
        ra = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        
        ser.write(b":GD#")
        time.sleep(0.2)
        dec = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        
        ser.close()
        
        if ra and dec:
            print(f"La monture sur {port} indique : AD={ra} / DEC={dec}")
    except Exception as e:
        pass
