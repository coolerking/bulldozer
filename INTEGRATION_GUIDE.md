# Bulldozer Integration Guide

## Overview
This guide provides step-by-step instructions for integrating the bulldozer-specific components with your Donkeycar system.

## Prerequisites

### Hardware Requirements
- Raspberry Pi (3B+ or newer recommended)
- 2x DC motors for tracks (left and right)
- L298N or similar motor driver board
- Nintendo Switch Pro Controller (or compatible Bluetooth controller)
- Motor power supply (6-12V depending on motors)
- Jumper wires and breadboard

### Software Requirements
- Donkeycar installed on Raspberry Pi
- Python 3.7+
- Required Python packages:
  ```bash
  pip3 install gpiozero evdev
  ```

## Hardware Wiring

### GPIO Pin Configuration (Default)
- **Left Motor:**
  - Forward: GPIO 17
  - Backward: GPIO 27
  - Enable (PWM): GPIO 22
- **Right Motor:**
  - Forward: GPIO 23
  - Backward: GPIO 24
  - Enable (PWM): GPIO 25

### Motor Driver Connections
1. Connect motor driver power to Pi's 5V and GND
2. Connect motor driver logic pins to specified GPIO pins
3. Connect motor power (external supply) to motor driver
4. Connect motors to motor driver outputs

## Software Setup

### 1. Enable Configuration
Uncomment the bulldozer-specific configuration in `myconfig.py`:

```python
# In myconfig.py, uncomment these sections:
BULLDOZER_DRIVE_TRAIN_TYPE = "GPIO_MOTORS"

BULLDOZER_MOTORS = {
    "LEFT_MOTOR_FORWARD_PIN": 17,
    "LEFT_MOTOR_BACKWARD_PIN": 27,
    "LEFT_MOTOR_ENABLE_PIN": 22,
    "RIGHT_MOTOR_FORWARD_PIN": 23,
    "RIGHT_MOTOR_BACKWARD_PIN": 24,
    "RIGHT_MOTOR_ENABLE_PIN": 25,
    "PWM_FREQUENCY": 1000,
    "STOP_PWM": 0,
    "MAX_PWM": 1.0,
}

# Nintendo Switch Controller
CONTROLLER_TYPE = 'custom'
USE_JOYSTICK_AS_DEFAULT = True
```

### 2. Pair Nintendo Switch Controller

#### For Nintendo Switch Pro Controller:
1. On Raspberry Pi:
   ```bash
   sudo bluetoothctl
   ```
2. In bluetoothctl:
   ```
   power on
   agent on
   default-agent
   scan on
   ```
3. On Pro Controller:
   - Hold SYNC button for 3 seconds until LEDs start flashing
4. In bluetoothctl:
   ```
   pair XX:XX:XX:XX:XX:XX  # Controller MAC address
   trust XX:XX:XX:XX:XX:XX
   connect XX:XX:XX:XX:XX:XX
   ```
5. Exit bluetoothctl:
   ```
   quit
   ```

#### Verify Controller:
```bash
ls /dev/input/
# Should show js0 or similar
```

### 3. Test Components

#### Test Actuator:
```bash
cd /home/hori/projects/agents/bulldozer
python3 parts/actuator.py
```

#### Test Controller:
```bash
cd /home/hori/projects/agents/bulldozer
python3 parts/controller.py
```

## Donkeycar Integration

### 1. Create Custom Manage Script
Create `manage_bulldozer.py`:

```python
#!/usr/bin/env python3
"""
Custom manage.py for bulldozer with Nintendo Switch controller
"""

import os
import sys
import logging
from docopt import docopt

# Add parts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'parts'))

from actuator import get_bulldozer_actuator
from controller import get_switch_controller

def drive(cfg):
    """Drive mode with bulldozer components"""
    from donkeycar.vehicle import Vehicle
    
    V = Vehicle(cfg)
    
    # Add bulldozer actuator
    actuator = get_bulldozer_actuator(cfg)
    V.add(actuator, inputs=['user/angle', 'user/throttle'], outputs=['left_speed', 'right_speed'])
    
    # Add Nintendo Switch controller
    controller = get_switch_controller(cfg)
    V.add(controller, outputs=['user/angle', 'user/throttle', 'recording'])
    
    # Start vehicle
    V.start()

if __name__ == '__main__':
    # Standard donkeycar startup
    from donkeycar import load_config
    cfg = load_config()
    drive(cfg)
```

### 2. Run Bulldozer
```bash
# Manual control mode
python3 manage_bulldozer.py drive

# With camera and recording
python3 manage_bulldozer.py drive --js
```

## Controller Mapping

### Nintendo Switch Pro Controller:
- **Left Stick X:** Steering (left/right)
- **Left Stick Y:** Throttle (forward/backward)
- **A Button:** Start/Stop recording
- **B Button:** Emergency stop
- **D-Pad:** Digital steering and throttle

### Control Sensitivity:
- Steering: 1.0 (full sensitivity)
- Throttle: 0.8 (80% max speed)
- Deadzone: 0.05 (5% input deadzone)

## Troubleshooting

### Common Issues

#### Controller Not Found
```bash
# Check if controller is paired
bluetoothctl devices Paired

# Check if device exists
ls -la /dev/input/js*

# Check permissions
sudo usermod -a -G input $USER
# Logout and login for changes to take effect
```

#### Motor Not Responding
```bash
# Check GPIO permissions
sudo usermod -a -G gpio $USER
# Logout and login for changes to take effect

# Test GPIO with gpiozero
python3 -c "from gpiozero import LED; led = LED(17); led.on()"
```

#### Permission Issues
```bash
# Add user to required groups
sudo usermod -a -G bluetooth,input,gpio $USER

# Reboot to apply changes
sudo reboot
```

### Debug Mode
Enable debug logging:
```bash
python3 manage_bulldozer.py drive --log=DEBUG
```

### Testing Individual Components

#### Test GPIO pins:
```python
# test_gpio.py
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
for pin in [17, 27, 22, 23, 24, 25]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(pin, GPIO.LOW)
GPIO.cleanup()
```

#### Test motors manually:
```python
# test_motors.py
from parts.actuator import BulldozerActuator

config = {
    'BULLDOZER_MOTORS': {
        'LEFT_MOTOR_FORWARD_PIN': 17,
        'LEFT_MOTOR_BACKWARD_PIN': 27,
        'LEFT_MOTOR_ENABLE_PIN': 22,
        'RIGHT_MOTOR_FORWARD_PIN': 23,
        'RIGHT_MOTOR_BACKWARD_PIN': 24,
        'RIGHT_MOTOR_ENABLE_PIN': 25,
    }
}

actuator = BulldozerActuator(config)
actuator.run(0.5, 0.0)  # Forward
```

## Safety Notes

1. **Always test with wheels off the ground first**
2. **Keep emergency stop button (B) easily accessible**
3. **Start with low throttle values during testing**
4. **Ensure proper motor power supply capacity**
5. **Check motor driver current ratings**

## Performance Tuning

### Adjust Control Sensitivity:
In `myconfig.py`:
```python
BULLDOZER_CONTROL = {
    "MIN_THROTTLE": 0.2,        # Reduce for more precise control
    "TURN_SENSITIVITY": 0.6,    # Reduce for smoother steering
    "ENABLE_SOFT_START": True,  # Gradual acceleration
}

JOYSTICK_MAX_THROTTLE = 0.6     # Reduce max speed
JOYSTICK_STEERING_SCALE = 0.8   # Reduce steering sensitivity
```

### Monitor System Performance:
```bash
# Check CPU usage
top

# Monitor GPIO access
gpio readall

# Check controller connection
sudo evtest /dev/input/js0
```

## Next Steps

1. **Calibrate steering** using `donkey calibrate`
2. **Collect training data** with manual driving
3. **Train AI model** using collected data
4. **Test autonomous mode** in safe environment
5. **Fine-tune parameters** based on performance