# Emergency Stop System Documentation

## Overview

The emergency stop system provides immediate motor shutdown capability for safety-critical situations. It monitors a GPIO pin for an emergency stop button press and immediately sets all motor controls to zero when triggered.

## Features

- **Immediate Stop**: Instantly stops all motors when emergency button is pressed
- **GPIO Monitoring**: Uses hardware GPIO pins for reliable button detection
- **Debouncing**: Configurable debounce time to prevent false triggers
- **Reset Functionality**: Optional reset button to resume normal operation
- **Fail-Safe**: Continues normal operation if GPIO libraries are unavailable
- **Configurable**: All parameters can be customized via configuration

## Hardware Setup

### Required Components
- Emergency stop button (normally open momentary switch)
- Optional reset button (normally open momentary switch)
- Jumper wires and resistors

### Wiring Diagram

```
Emergency Stop Button:
┌─────────┐
│         │
│  Button │ GPIO Pin (e.g., 26) ─┐
│         │                      │
└─────────┘                      │
    │                           │
    └─ GND ─────────────────────┘

Optional Reset Button:
┌─────────┐
│         │
│  Button │ GPIO Pin (e.g., 19) ─┐
│         │                      │
└─────────┘                      │
    │                           │
    └─ GND ─────────────────────┘
```

## Configuration

### Basic Configuration
Add these settings to your `myconfig.py`:

```python
# Enable emergency stop system
HAVE_EMERGENCY_STOP = True

# GPIO pin for emergency stop button (BCM numbering)
EMERGENCY_STOP_PIN = 26

# Use internal pull-up resistor (recommended)
EMERGENCY_PULLUP = True

# Debounce time in seconds
EMERGENCY_DEBOUNCE_TIME = 0.1

# Optional reset button pin (set to None to disable)
EMERGENCY_RESET_PIN = 19
```

### Advanced Configuration
For more control, you can use the bulldozer-specific configuration:

```python
# Bulldozer emergency stop configuration
BULLDOZER_EMERGENCY_STOP = {
    "EMERGENCY_STOP_PIN": 26,
    "EMERGENCY_PULLUP": True,
    "EMERGENCY_DEBOUNCE_TIME": 0.1,
    "EMERGENCY_RESET_PIN": 19,
}
```

## Usage

### Enabling Emergency Stop
1. Uncomment and configure the emergency stop settings in `myconfig.py`
2. Wire your emergency stop button to the configured GPIO pin
3. Start the vehicle normally with `python manage.py drive`

### Emergency Stop Operation
- **Trigger**: Press the emergency stop button
- **Effect**: All motors immediately stop (throttle and steering set to 0.0)
- **Reset**: If reset button is configured, press it to resume normal operation
- **Status**: Check logs or web interface for emergency stop status

### Testing

Run the test script to verify functionality:
```bash
python test_emergency_stop.py
```

## GPIO Pin Information

### Compatible Pins (BCM numbering)
- **Emergency Stop Pin**: Any GPIO pin (2, 3, 4, 14, 15, 17, 18, 27, 22, 23, 24, 10, 9, 25, 11, 8, 7)
- **Reset Pin**: Any GPIO pin (same as above)

### Pin Configuration
- **Pull-up Mode**: Button connects pin to GND when pressed (recommended)
- **Pull-down Mode**: Button connects pin to 3.3V when pressed
- **Debouncing**: Prevents multiple triggers from button bounce

## Troubleshooting

### Common Issues

1. **Emergency stop not working**
   - Check GPIO pin connections
   - Verify RPi.GPIO library is installed: `pip install RPi.GPIO`
   - Check configuration values in myconfig.py

2. **False triggers**
   - Increase debounce time: `EMERGENCY_DEBOUNCE_TIME = 0.2`
   - Use shorter wires for button connections
   - Add external pull-up resistor (10kΩ)

3. **GPIO errors**
   - Check for pin conflicts with other hardware
   - Ensure proper GPIO permissions: `sudo usermod -a -G gpio pi`
   - Verify BCM pin numbering (not physical pin numbers)

### Debug Mode
Enable verbose logging to troubleshoot issues:
```python
# In myconfig.py
LOGGING_LEVEL = 'DEBUG'
```

## Safety Considerations

- **Always test emergency stop before operation**
- **Use normally open switches for fail-safe operation**
- **Consider adding visual indicators for emergency stop status**
- **Document emergency procedures for operators**
- **Regular testing and maintenance of emergency systems**

## Integration with Other Systems

The emergency stop system integrates with:
- **Drive Mode**: Overrides any drive mode (user, auto-pilot, etc.)
- **Web Interface**: Status available through web controller
- **Logging**: All emergency events logged with timestamps
- **Shutdown**: Proper GPIO cleanup on program exit

## Example Implementation

### Basic Wiring for Raspberry Pi
```
Emergency Stop Button:
- One terminal to GPIO 26 (BCM)
- Other terminal to GND (Pin 6)

Reset Button (optional):
- One terminal to GPIO 19 (BCM)  
- Other terminal to GND (Pin 9)
```

### Configuration Example
```python
# myconfig.py
HAVE_EMERGENCY_STOP = True
EMERGENCY_STOP_PIN = 26
EMERGENCY_PULLUP = True
EMERGENCY_DEBOUNCE_TIME = 0.1
EMERGENCY_RESET_PIN = 19
```