#!/usr/bin/env python3
"""
Standalone emergency stop test
Tests the EmergencyStop class without external dependencies
"""

import sys
import os
import time

class MockLogger:
    """Mock logger for testing"""
    @staticmethod
    def info(msg):
        print(f"INFO: {msg}")
    
    @staticmethod
    def error(msg):
        print(f"ERROR: {msg}")
    
    @staticmethod
    def warning(msg):
        print(f"WARNING: {msg}")

class MockConfig:
    """Mock configuration class for testing"""
    def __init__(self):
        self.EMERGENCY_STOP_PIN = 26
        self.EMERGENCY_PULLUP = True
        self.EMERGENCY_DEBOUNCE_TIME = 0.1
        self.EMERGENCY_RESET_PIN = None

class EmergencyStop:
    """
    Emergency stop system that monitors a GPIO pin for emergency stop button press.
    Immediately stops all motors when triggered and provides reset mechanism.
    """
    
    def __init__(self, config):
        """
        Initialize emergency stop system
        
        :param config: Configuration dictionary containing emergency stop parameters
        """
        self.config = config
        self.emergency_pin = getattr(config, 'EMERGENCY_STOP_PIN', 26)
        self.debounce_time = getattr(config, 'EMERGENCY_DEBOUNCE_TIME', 0.1)
        self.pull_up = getattr(config, 'EMERGENCY_PULLUP', True)
        self.reset_pin = getattr(config, 'EMERGENCY_RESET_PIN', None)
        
        # Emergency stop state
        self.is_triggered = False
        self.last_trigger_time = 0
        
        # GPIO handling (simplified for testing)
        self.gpio_available = False
        
        try:
            # Try to import GPIO (will fail in test environment)
            import RPi.GPIO as GPIO
            self.gpio_available = True
            MockLogger.info(f"Emergency stop initialized: pin={self.emergency_pin}")
        except ImportError:
            MockLogger.warning("RPi.GPIO not available - running in simulation mode")
            self.gpio_available = False
    
    def run(self, throttle, steering):
        """
        Check emergency stop state and return appropriate control values
        
        :param throttle: Input throttle value (-1.0 to 1.0)
        :param steering: Input steering value (-1.0 to 1.0)  
        :return: tuple of (emergency_active, throttle, steering) where emergency_active is True if triggered
        """
        import time
        
        # Return emergency state and zeroed controls if triggered
        if self.is_triggered:
            return True, 0.0, 0.0
        else:
            return False, throttle, steering
    
    def trigger_emergency(self):
        """Manually trigger emergency stop for testing"""
        self.is_triggered = True
        MockLogger.error("EMERGENCY STOP TRIGGERED!")
    
    def reset_emergency(self):
        """Manually reset emergency stop for testing"""
        self.is_triggered = False
        MockLogger.info("Emergency stop reset")
    
    def get_status(self):
        """Return current emergency stop status"""
        return {"emergency_triggered": self.is_triggered}

def test_emergency_stop():
    """Test emergency stop functionality"""
    print("=== Emergency Stop Standalone Test ===")
    
    # Create mock config
    config = MockConfig()
    
    # Test emergency stop initialization
    print("1. Testing EmergencyStop initialization...")
    emergency_stop = EmergencyStop(config)
    
    # Test normal operation
    print("2. Testing normal operation...")
    emergency_active, throttle, steering = emergency_stop.run(0.5, 0.2)
    print(f"   Emergency active: {emergency_active}")
    print(f"   Throttle: {throttle}, Steering: {steering}")
    
    # Test emergency trigger
    print("3. Testing emergency trigger...")
    emergency_stop.trigger_emergency()
    emergency_active, throttle, steering = emergency_stop.run(0.5, 0.2)
    print(f"   Emergency active: {emergency_active}")
    print(f"   Throttle: {throttle}, Steering: {steering}")
    
    # Test reset functionality
    print("4. Testing reset functionality...")
    emergency_stop.reset_emergency()
    emergency_active, throttle, steering = emergency_stop.run(0.5, 0.2)
    print(f"   Emergency active: {emergency_active}")
    print(f"   Throttle: {throttle}, Steering: {steering}")
    
    # Test status
    print("5. Testing status...")
    status = emergency_stop.get_status()
    print(f"   Status: {status}")
    
    print("=== Emergency Stop Test Complete ===")
    return True

if __name__ == "__main__":
    try:
        test_emergency_stop()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()