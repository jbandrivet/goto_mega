import sys
import os
import time

# Add the project directory to path so we can import goto_universal
sys.path.append("/media/jean-baptiste/6E91-2E1D/perso/astronomie/gotos/goto_universale")

from goto_universal import Settings, Mount, Astro

def main():
    cfg = Settings()
    
    print("Initializing Mount in Simulation Mode...")
    m = Mount(cfg)
    
    print("Connecting...")
    ok = m.connect(port="SIM", baud=9600, sim=True)
    if not ok:
        print("Failed to connect!")
        sys.exit(1)
        
    print("Connected successfully!")
    
    # Wait for status loop to retrieve initial coordinates
    time.sleep(1.5)
    print(f"Initial positions: RA={Astro.fmt_ra(m.state.ra_h)}, DEC={Astro.fmt_dec(m.state.dec_d)}")
    print(f"Initial Az={m.state.az_d:.2f}°, Alt={m.state.alt_d:.2f}°")
    
    # Set speed to 15 degrees/sec for faster simulation
    m.set_speed(15.0)
    print("Slew speed set to 15.0°/s")
    
    # Target coordinates: RA 12h 30m 00s, DEC +45d 00m 00s
    tgt_ra = 12.5  # 12.5 hours
    tgt_dec = 45.0  # +45 degrees
    
    # Calculate expected target Alt/Az at current LST
    lat = cfg.get("latitude", 45.764)
    expected_az, expected_alt = Astro.eq_to_horiz(tgt_ra, tgt_dec, m.state.lst_h, lat)
    print(f"Expected Target horizontal: Az={expected_az:.2f}°, Alt={expected_alt:.2f}°")
    
    print(f"Triggering GoTo to RA={Astro.fmt_ra(tgt_ra)}, DEC={Astro.fmt_dec(tgt_dec)}")
    resp = m.goto(tgt_ra, tgt_dec)
    print(f"GoTo response: '{resp}'")
    
    if not resp.startswith("0"):
        print("GoTo command rejected!")
        m.disconnect()
        sys.exit(1)
        
    print("Slew started. Monitoring progress...")
    
    reached = False
    for i in range(40):
        time.sleep(0.5)
        print(f"Step {i:02d}: RA={Astro.fmt_ra(m.state.ra_h)} | DEC={Astro.fmt_dec(m.state.dec_d)} | Az={m.state.az_d:.2f}° | Alt={m.state.alt_d:.2f}° | slewing={m.state.slewing}")
        if not m.state.slewing:
            # Slew complete, check proximity to expected Alt/Az
            diff_az = abs((m.state.az_d - expected_az + 180) % 360 - 180)
            diff_alt = abs(m.state.alt_d - expected_alt)
            print(f"\nSlew finished. Differences to target: Diff_Az={diff_az:.4f}°, Diff_Alt={diff_alt:.4f}°")
            if diff_az < 1.0 and diff_alt < 1.0:
                print("GoTo reached target Alt/Az destination successfully!")
                reached = True
                break
            else:
                print("Slewing stopped but target coordinates not matched.")
                break
            
    m.disconnect()
    
    if reached:
        print("\n*** TEST SUCCESSFUL ***")
        sys.exit(0)
    else:
        print("\n*** TEST FAILED ***")
        sys.exit(1)

if __name__ == "__main__":
    main()
