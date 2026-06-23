#!/usr/bin/env python3
import serial
import time
import sys
import math
from datetime import datetime

def parse_lx_lat(raw):
    # Format: +DD*MM:SS or +DD*MM
    sign = -1.0 if raw[0] == '-' else 1.0
    parts = raw[1:].replace('*', ':').split(':')
    d = float(parts[0])
    m = float(parts[1]) if len(parts) > 1 else 0.0
    s = float(parts[2]) if len(parts) > 2 else 0.0
    return sign * (d + m/60.0 + s/3600.0)

def format_ra(hours):
    h = int(hours)
    m = int((hours - h) * 60)
    s = int(((hours - h) * 60 - m) * 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_dec(deg):
    sign = '+' if deg >= 0 else '-'
    val = abs(deg)
    d = int(val)
    m = int((val - d) * 60)
    s = int(((val - d) * 60 - m) * 60)
    return f"{sign}{d:02d}*{m:02d}:{s:02d}"

def test_drift_safety():
    port = "/dev/ttyACM0"
    baud = 38400
    print(f"Connecting to Arduino on {port} at {baud} baud...")
    
    try:
        ser = serial.Serial(port, baud, timeout=1.5)
        # Wait for reboot
        time.sleep(2.0)
        ser.reset_input_buffer()
        
        # Handshake
        resp = ""
        for attempt in range(3):
            ser.write(b":GVP#")
            resp = ser.read_until(b"#").decode('ascii', errors='ignore')
            if "OnStep" in resp:
                break
            time.sleep(0.5)
            
        if "OnStep" not in resp:
            print("Error: Handshake failed.")
            ser.close()
            sys.exit(1)
        print("Handshake success. Connected to OnStep device.")
        
        # 1. Synchronize Time
        print("\nSynchronizing Arduino clock with PC clock...")
        now = datetime.now()
        # Date
        ser.write(f":SC{now.month:02d}/{now.day:02d}/{now.year%100:02d}#".encode('ascii'))
        ser.read_until(b"#")
        ser.read_until(b"#")
        # Time
        ser.write(f":SL{now.hour:02d}:{now.minute:02d}:{now.second:02d}#".encode('ascii'))
        ser.read_until(b"#")
        # Timezone
        utc_offset = -time.timezone / 3600.0
        if time.daylight and time.localtime().tm_isdst:
            utc_offset = -time.altzone / 3600.0
        sign = '+' if utc_offset >= 0 else '-'
        ser.write(f":SG{sign}{int(abs(utc_offset)):02d}#".encode('ascii'))
        ser.read_until(b"#")
        print("Clock synchronized.")
        
        # Unpark if parked
        ser.write(b":hQ#")
        park_status = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        if park_status == '1':
            print("Mount is parked. Sending unpark command (:hR#)...")
            ser.write(b":hR#")
            ser.read_until(b"#")
            time.sleep(1.0)
            
        # 2. Get Latitude and LST from Arduino
        ser.write(b":Gt#")
        lat_raw = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        lat_val = parse_lx_lat(lat_raw)
        print(f"Latitude parsed from mount: {lat_val:.4f}°")
        
        ser.write(b":GS#")
        lst_raw = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
        lst_parts = lst_raw.split(':')
        lst_hours = float(lst_parts[0]) + float(lst_parts[1])/60.0 + float(lst_parts[2])/3600.0
        print(f"LST parsed from mount: {lst_raw} ({lst_hours:.4f} hours)")
        
        # 3. Calculate RA and DEC for setting target
        # Target: Altitude = -0.8 degrees, Azimuth = 270.0 degrees (West, setting)
        target_alt = -0.8
        target_az = 270.0
        
        alt_r = math.radians(target_alt)
        az_r = math.radians(target_az)
        lat_r = math.radians(lat_val)
        
        sin_dec = math.sin(alt_r) * math.sin(lat_r) + math.cos(alt_r) * math.cos(lat_r) * math.cos(az_r)
        dec_r = math.asin(sin_dec)
        dec_val = math.degrees(dec_r)
        
        cos_ha = (math.sin(alt_r) - math.sin(dec_r) * math.sin(lat_r)) / (math.cos(dec_r) * math.cos(lat_r))
        cos_ha = max(-1.0, min(1.0, cos_ha))
        ha_r = math.acos(cos_ha)
        ha_val = math.degrees(ha_r)
        
        ha_hours = ha_val / 15.0
        ra_hours = lst_hours - ha_hours
        if ra_hours < 0:
            ra_hours += 24.0
        if ra_hours >= 24.0:
            ra_hours -= 24.0
            
        ra_str = format_ra(ra_hours)
        dec_str = format_dec(dec_val)
        print(f"\nCalculated coordinates for Alt={target_alt}°, Az={target_az}°:")
        print(f"  Target RA:  {ra_str} ({ra_hours:.4f} hours)")
        print(f"  Target DEC: {dec_str} ({dec_val:.4f}°)")
        
        # Send targets
        ser.write(f":Sr{ra_str}#".encode('ascii'))
        ser.read_until(b"#")
        ser.write(f":Sd{dec_str}#".encode('ascii'))
        ser.read_until(b"#")
        
        # Synchronize mount (sets current position to Alt=-0.8°, Az=270°)
        print("\nSynchronizing mount position using :CM#...")
        ser.write(b":CM#")
        sync_reply = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"  Sync response: {repr(sync_reply)}")
        
        # Enable tracking
        print("\nActivating tracking (:Te#)...")
        ser.write(b":Te#")
        track_reply = ser.read_until(b"#").decode('ascii', errors='ignore')
        print(f"  Tracking activation response: {repr(track_reply)}")
        
        # Poll GBE telemetry in loop
        print("\nMonitoring tracking drift (limit is -1.0°)...")
        start_time = time.time()
        safety_triggered = False
        
        # 120 iterations of 1s (max 2 minutes)
        for i in range(120):
            # Check GBE
            ser.write(b":GBE#")
            telemetry = ser.read_until(b"#").decode('ascii', errors='ignore').strip('#')
            parts = telemetry.split(',')
            
            if len(parts) >= 8:
                tracking_flag = parts[0]
                slewing_flag = parts[1]
                limit_hit = parts[2]
                curr_alt = float(parts[4])
                curr_az = float(parts[5])
                parked_flag = parts[6]
                
                print(f"Time: {time.time() - start_time:4.1f}s | Alt: {curr_alt:7.4f}° | Az: {curr_az:8.4f}° | Track: {tracking_flag} | LimitHit: {limit_hit} | Parked: {parked_flag}")
                
                if parked_flag == '1':
                    print("\n[SAFETY SYSTEM TRIGGERED AND RETURN-TO-PARK COMPLETED]")
                    print(f"  Final Altitude: {curr_alt:.4f}° (Zenith/Park)")
                    print(f"  Tracking State: {tracking_flag} (0 = Stopped)")
                    print(f"  Limit Hit Flag: {limit_hit} (1 = Active)")
                    print(f"  Parked Flag:    {parked_flag} (1 = Parked)")
                    safety_triggered = True
                    break
            else:
                print(f"Invalid telemetry: {telemetry}")
                
            time.sleep(2.0)
            
        if safety_triggered:
            # Play a warning beep
            print("\nPlaying safety warning beep on mount buzzer...")
            ser.write(b":Bbp#")
            ser.read_until(b"#")
            print("Test COMPLETED successfully!")
        else:
            print("\nTest TIMEOUT: Safety limit did not trigger within 2 minutes.")
            
        ser.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_drift_safety()
