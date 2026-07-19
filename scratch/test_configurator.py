#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import tkinter as tk
from pathlib import Path
import json

# Import the configurator tool classes
sys.path.append(str(Path(__file__).parent.parent))
import goto_andrivet_config_tool as config_tool

class TestConfiguratorLogic(unittest.TestCase):

    def setUp(self):
        # Prevent the config tool from writing to the actual user home config
        self.temp_config_path = Path("/tmp/test_config_tool_settings.json")
        if self.temp_config_path.exists():
            self.temp_config_path.unlink()
        
        # Patch the CONFIG_FILE path in the module
        self.path_patcher = patch("goto_andrivet_config_tool.CONFIG_FILE", self.temp_config_path)
        self.path_patcher.start()

    def tearDown(self):
        self.path_patcher.stop()
        if self.temp_config_path.exists():
            self.temp_config_path.unlink()

    def test_translation_keys_matching(self):
        """Verify that English and French translation dicts have identical keys."""
        en_keys = set(config_tool.TRANSLATIONS["en"].keys())
        fr_keys = set(config_tool.TRANSLATIONS["fr"].keys())
        self.assertEqual(en_keys, fr_keys, "Translation dictionaries should have the same set of keys.")

    def test_coordinate_parsing_and_formatting(self):
        """Verify parsing LX200 coordinate strings to floats and formatting floats to LX200 strings."""
        app = config_tool.ConfigToolApp()
        
        # Test Latitude formatting and parsing
        # format_lat_lx returns sign + DD * MM : SS
        lat = 43.9694
        formatted_lat = app.format_lat_lx(lat)
        self.assertEqual(formatted_lat, "+43*58:09")
        parsed_lat = app.parse_lx_coords(formatted_lat)
        self.assertAlmostEqual(parsed_lat, lat, places=3)
        
        # Negative latitude
        lat_neg = -22.9068
        formatted_lat_neg = app.format_lat_lx(lat_neg)
        self.assertEqual(formatted_lat_neg, "-22*54:24")
        parsed_lat_neg = app.parse_lx_coords(formatted_lat_neg)
        self.assertAlmostEqual(parsed_lat_neg, lat_neg, places=3)

        # Test Longitude formatting and parsing
        # format_lon_lx returns sign + DDD * MM : SS
        lon = 6.3753
        formatted_lon = app.format_lon_lx(lon)
        self.assertEqual(formatted_lon, "+006*22:31")
        parsed_lon = app.parse_lx_coords(formatted_lon)
        self.assertAlmostEqual(parsed_lon, lon, places=3)
        
        lon_neg = -43.1729
        formatted_lon_neg = app.format_lon_lx(lon_neg)
        self.assertEqual(formatted_lon_neg, "-043*10:22")
        parsed_lon_neg = app.parse_lx_coords(formatted_lon_neg)
        self.assertAlmostEqual(parsed_lon_neg, lon_neg, places=3)
        
        app.destroy()

    def test_settings_load_and_save(self):
        """Verify settings are correctly read from and written to local configuration file."""
        # Create a mock config file content
        custom_settings = {
            "mount_port": "/dev/ttyTestPort",
            "mount_baud": 115200,
            "gear_ratio_az": 800.0,
            "gear_ratio_alt": 900.0,
            "mount_type": "GermanEq",
            "obs_lat": 45.0,
            "obs_lon": 5.0,
            "slew_speed": 4.5,
            "buzzer_on": False,
            "steps_per_rev_motor": 400,
            "microstep": 64,
            "language": "en"
        }
        self.temp_config_path.write_text(json.dumps(custom_settings))

        app = config_tool.ConfigToolApp()
        
        # Check if loaded settings match the file contents
        self.assertEqual(app.settings["mount_port"], "/dev/ttyTestPort")
        self.assertEqual(app.settings["mount_baud"], 115200)
        self.assertEqual(app.settings["gear_ratio_az"], 800.0)
        self.assertEqual(app.settings["gear_ratio_alt"], 900.0)
        self.assertEqual(app.settings["mount_type"], "GermanEq")
        self.assertEqual(app.settings["obs_lat"], 45.0)
        self.assertEqual(app.settings["obs_lon"], 5.0)
        self.assertEqual(app.settings["slew_speed"], 4.5)
        self.assertEqual(app.settings["buzzer_on"], False)
        self.assertEqual(app.settings["steps_per_rev_motor"], 400)
        self.assertEqual(app.settings["microstep"], 64)
        self.assertEqual(app.settings["language"], "en")

        # Update setting and save
        app.settings["language"] = "fr"
        app.save_local_settings()
        
        saved_data = json.loads(self.temp_config_path.read_text())
        self.assertEqual(saved_data["language"], "fr")
        
        app.destroy()

    def test_language_translation_switching(self):
        """Test toggling language in GUI updates label values appropriately."""
        app = config_tool.ConfigToolApp()
        
        # Switch to English
        app.change_language("en")
        self.assertEqual(app.lbl_port.cget("text"), "Port:")
        self.assertEqual(app.lbl_baud.cget("text"), "Baud:")
        self.assertEqual(app.lbl_lang.cget("text"), "Language / Langue:")
        self.assertEqual(app.form_lf.cget("text"), "Telescope Mount parameters")
        
        # Switch to French
        app.change_language("fr")
        self.assertEqual(app.lbl_port.cget("text"), "Port :")
        self.assertEqual(app.lbl_baud.cget("text"), "Baud :")
        self.assertEqual(app.lbl_lang.cget("text"), "Langue :")
        self.assertEqual(app.form_lf.cget("text"), "Paramètres de la Monture")
        
        app.destroy()

    @patch("serial.Serial")
    def test_serial_handshake_success(self, mock_serial_class):
        """Test serial connection handshake success when device returns 'OnStep'."""
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        
        # Simulate OnStep response to handshake command :GVP# and beep response to :Bbp#
        mock_serial.read_until.side_effect = [b"OnStep#", b"#"]

        app = config_tool.ConfigToolApp()
        app.port_var.set("/dev/ttyACM0")
        app.baud_var.set("38400")

        # Suppress showinfo dialog
        with patch("tkinter.messagebox.showinfo") as mock_showinfo:
            app.toggle_connection()
            
            self.assertTrue(app.is_connected)
            mock_serial_class.assert_called_with("/dev/ttyACM0", 38400, timeout=1.5)
            mock_serial.write.assert_any_call(b":GVP#")
            mock_serial.write.assert_any_call(b":Bbp#")
            mock_showinfo.assert_called_once()
            
        app.destroy()

    @patch("serial.Serial")
    def test_serial_handshake_failure(self, mock_serial_class):
        """Test serial connection handshake failure when device returns invalid response."""
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        
        # Return something else or empty bytes
        mock_serial.read_until.return_value = b"UnknownResponse#"

        app = config_tool.ConfigToolApp()
        app.port_var.set("/dev/ttyACM0")
        app.baud_var.set("38400")

        with patch("tkinter.messagebox.showerror") as mock_showerror:
            app.toggle_connection()
            
            self.assertFalse(app.is_connected)
            mock_serial.close.assert_called_once()
            mock_showerror.assert_called_once_with("Error", "Device on this port did not respond to GotoMega OnStep protocol.")
            
        app.destroy()

    @patch("serial.Serial")
    def test_apply_config_to_arduino(self, mock_serial_class):
        """Verify commands sent to Arduino when applying/saving configuration."""
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.read_until.side_effect = [b"OnStep#", b"#"] # for connect

        app = config_tool.ConfigToolApp()
        
        # Populate the GUI fields with test configuration
        app.mount_type_var.set("AltAz")
        app.steps_entry.delete(0, tk.END)
        app.steps_entry.insert(0, "200")
        app.microstep_var.set("32")
        app.gear_az_entry.delete(0, tk.END)
        app.gear_az_entry.insert(0, "750.0")
        app.gear_alt_entry.delete(0, tk.END)
        app.gear_alt_entry.insert(0, "750.0")
        app.lat_entry.delete(0, tk.END)
        app.lat_entry.insert(0, "43.9694")
        app.lon_entry.delete(0, tk.END)
        app.lon_entry.insert(0, "6.3753")
        app.speed_scale.set(2.0)
        app.buzzer_var.set(True)

        # Connect the application manually
        app.ser = mock_serial
        app.is_connected = True
        app.update_connection_status()

        # Mock read_until response for the apply operations (1 command for each setting, total 9 settings)
        mock_serial.read_until.side_effect = [b"#"] * 15

        with patch("tkinter.messagebox.showinfo") as mock_showinfo:
            app.apply_config_to_arduino()
            
            # Verify serial command sequence and format
            mock_serial.write.assert_any_call(b":BMa#") # AltAz command
            mock_serial.write.assert_any_call(b":BSp200#") # Motor steps
            mock_serial.write.assert_any_call(b":BSm32#") # Microstepping
            mock_serial.write.assert_any_call(b":BGa750.0#") # Az Gear ratio
            mock_serial.write.assert_any_call(b":BGe750.0#") # Alt Gear ratio
            mock_serial.write.assert_any_call(b":St+43*58:09#") # Lat (+43.9694)
            mock_serial.write.assert_any_call(b":Sg+006*22:31#") # Lon (+6.3753)
            mock_serial.write.assert_any_call(b":BV 20#") # Slew speed 2.0 -> 20
            mock_serial.write.assert_any_call(b":Bb1#") # Buzzer enabled
            
            mock_showinfo.assert_called_once_with("Apply Config", "Configuration successfully saved to Arduino Mega!")
            
        app.destroy()

if __name__ == "__main__":
    unittest.main()
