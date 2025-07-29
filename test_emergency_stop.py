#!/usr/bin/env python3
"""
Test script for emergency stop functionality

Usage:
    python test_emergency_stop.py
"""

import sys
import os
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from manage import EmergencyStop

class MockConfig:
    """Mock configuration class for testing"""
    def __init__(self):
        self.EMERGENCY_STOP_PIN = 26
        self.EMERGENCY_PULLUP = True
        self.EMERGENCY_DEBOUNCE_TIME = 0.1
        self.EMERGENCY_RESET_PIN = None

def test_emergency_stop():
    """Test emergency stop functionality"""
    print("=== Emergency Stop Test ===")
    
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
    # Simulate emergency stop (in real hardware, this would be button press)
    emergency_stop.is_triggered = True
    emergency_active, throttle, steering = emergency_stop.run(0.5, 0.2)
    print(f"   Emergency active: {emergency_active}")
    print(f"   Throttle: {throttle}, Steering: {steering}")
    
    # Test reset functionality
    print("4. Testing reset functionality...")
    emergency_stop.is_triggered = False
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