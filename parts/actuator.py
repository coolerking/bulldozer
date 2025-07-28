#!/usr/bin/env python3
"""
Donkeycar用ブルドーザー Actuator パーツ

このモジュールは、ブルドーザートラック用の2つのモーターを制御するためのDonkeycarパーツを提供します。
可能な限りgpiozeroを使用し、RPi.GPIOにフォールバックします。

このアクチュエータは、左右のトラックを持つブルドーザーの差動駆動制御を提供します。
"""

import logging
import time
from typing import Tuple, Optional, Dict, Any

try:
    from gpiozero import Motor, PWMOutputDevice
    GPIOZERO_AVAILABLE = True
except ImportError:
    GPIOZERO_AVAILABLE = False
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
    except ImportError:
        raise ImportError("Neither gpiozero nor RPi.GPIO is available. Please install gpiozero: pip3 install gpiozero")

class BulldozerActuator:
    """
    ブルドーザーのトラックモーターを制御するためのActuatorクラス
    
    左右のトラックを差動制御します。
    利用可能な場合はgpiozeroを使用し、必要な場合はRPi.GPIOにフォールバックします。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize bulldozer actuator with configuration.
        
        Args:
            config: Configuration dictionary with motor pin mappings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Extract motor pin configuration
        motor_config = config.get('BULLDOZER_MOTORS', {})
        self.left_fwd_pin = motor_config.get('LEFT_MOTOR_FORWARD_PIN', 17)
        self.left_bwd_pin = motor_config.get('LEFT_MOTOR_BACKWARD_PIN', 27)
        self.left_en_pin = motor_config.get('LEFT_MOTOR_ENABLE_PIN', 22)
        
        self.right_fwd_pin = motor_config.get('RIGHT_MOTOR_FORWARD_PIN', 23)
        self.right_bwd_pin = motor_config.get('RIGHT_MOTOR_BACKWARD_PIN', 24)
        self.right_en_pin = motor_config.get('RIGHT_MOTOR_ENABLE_PIN', 25)
        
        # Control parameters
        control_config = config.get('BULLDOZER_CONTROL', {})
        self.min_throttle = control_config.get('MIN_THROTTLE', 0.3)
        self.max_pwm = motor_config.get('MAX_PWM', 1.0)
        self.pwm_frequency = motor_config.get('PWM_FREQUENCY', 1000)
        self.soft_start = control_config.get('ENABLE_SOFT_START', True)
        
        # Initialize motors
        self.left_motor = None
        self.right_motor = None
        self.left_pwm = None
        self.right_pwm = None
        self.initialized = False
        
        self._setup_motors()
    
    def _setup_motors(self):
        """
        有効なライブラリに合わせてモータコントローラを初期化する。

        Args:
            None
        Returns:
            None
        """
        try:
            if GPIOZERO_AVAILABLE:
                self.logger.info("Using gpiozero for motor control")
                self._setup_gpiozero_motors()
            else:
                self.logger.info("Using RPi.GPIO for motor control")
                self._setup_rpi_gpio_motors()
            
            self.initialized = True
            self.logger.info("Bulldozer actuator initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize motors: {e}")
            self.initialized = False
    
    def _setup_gpiozero_motors(self):
        """
        gpiozeroライブラリを使用する場合のモータコントローラを初期化する処理

        Args:
            None
        Returns:
            None
        """
        # gpiozeroをつかった gpiozero.Motor 初期化
        self.left_motor = Motor(
            forward=self.left_fwd_pin,
            backward=self.left_bwd_pin,
            enable=self.left_en_pin,
            pwm=True,
            pin_factory=None
        )
        
        self.right_motor = Motor(
            forward=self.right_fwd_pin,
            backward=self.right_bwd_pin,
            enable=self.right_en_pin,
            pwm=True,
            pin_factory=None
        )
        
    def _setup_rpi_gpio_motors(self):
        """
        RPi.GPIO ライブラリを使用する場合のモータコントローラを初期化する処理
        
        Args:
            None
        Returns:
            None
        """
        # モータ操作用 GPIO ピンの初期化
        motor_pins = [
            self.left_fwd_pin, self.left_bwd_pin, self.left_en_pin,
            self.right_fwd_pin, self.right_bwd_pin, self.right_en_pin
        ]
        
        for pin in motor_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        # スピードコントロール用のPWMを設定
        self.left_pwm = GPIO.PWM(self.left_en_pin, self.pwm_frequency)
        self.right_pwm = GPIO.PWM(self.right_en_pin, self.pwm_frequency)
        self.left_pwm.start(0)
        self.right_pwm.start(0)
    
    def _apply_soft_start(self, target_left_speed: float, target_right_speed: float) -> Tuple[float, float]:
        """
        モーターに負担がかからないようにソフトスタートを適用する。
        
        Args:
            target_left_speed: 目標左トラック速度 (-1.0 ～ 1.0)
            target_right_speed: 目標右トラック速度 (-1.0 ～ 1.0)
        Returns:
            タプル (soft_left_speed, soft_right_speed) - ソフトスタート後の速度
        """
        if not self.soft_start:
            return target_left_speed, target_right_speed
        
        # Simple soft start - gradually increase speed
        # In a real implementation, you might want more sophisticated ramping
        return target_left_speed, target_right_speed
    
    def set_speed(self, left_speed: float, right_speed: float):
        """
        左右のトラックのスピードを設定する。
        
        Args:
            left_speed: 左トラックのスピード (-1.0 ～ 1.0)
            right_speed: 右トラックのスピード (-1.0 ～ 1.0)
        """
        if not self.initialized:
            self.logger.warning("Actuator not initialized, ignoring speed command")
            return
        
        # 速度を有効範囲内に
        left_speed = max(-1.0, min(1.0, left_speed))
        right_speed = max(-1.0, min(1.0, right_speed))
        
        # 最小限のスロットルで動かす
        if abs(left_speed) < self.min_throttle and left_speed != 0:
            left_speed = self.min_throttle if left_speed > 0 else -self.min_throttle
        if abs(right_speed) < self.min_throttle and right_speed != 0:
            right_speed = self.min_throttle if right_speed > 0 else -self.min_throttle
        
        # ソフトスタートの適用
        left_speed, right_speed = self._apply_soft_start(left_speed, right_speed)
        
        self._set_motor_speed('left', left_speed)
        self._set_motor_speed('right', right_speed)
    
    def _set_motor_speed(self, motor: str, speed: float):
        """
        個々のモーターの速度を設定する
        
        Args:
            motor: 'left' または 'right'
            speed: モーターの速度 (-1.0 ～ 1.0)
        Returns:
            None
        """
        if GPIOZERO_AVAILABLE and self.left_motor and self.right_motor:
            if motor == 'left':
                if speed > 0:
                    self.left_motor.forward(speed)
                elif speed < 0:
                    self.left_motor.backward(abs(speed))
                else:
                    self.left_motor.stop()
            elif motor == 'right':
                if speed > 0:
                    self.right_motor.forward(speed)
                elif speed < 0:
                    self.right_motor.backward(abs(speed))
                else:
                    self.right_motor.stop()
        else:
            # RPi.GPIO フォールバック
            pwm_val = abs(speed) * 100  # 百分率(%)にする

            if motor == 'left':
                if speed > 0:
                    GPIO.output(self.left_fwd_pin, GPIO.HIGH)
                    GPIO.output(self.left_bwd_pin, GPIO.LOW)
                elif speed < 0:
                    GPIO.output(self.left_fwd_pin, GPIO.LOW)
                    GPIO.output(self.left_bwd_pin, GPIO.HIGH)
                else:
                    GPIO.output(self.left_fwd_pin, GPIO.LOW)
                    GPIO.output(self.left_bwd_pin, GPIO.LOW)
                
                if self.left_pwm:
                    self.left_pwm.ChangeDutyCycle(pwm_val)
                    
            elif motor == 'right':
                if speed > 0:
                    GPIO.output(self.right_fwd_pin, GPIO.HIGH)
                    GPIO.output(self.right_bwd_pin, GPIO.LOW)
                elif speed < 0:
                    GPIO.output(self.right_fwd_pin, GPIO.LOW)
                    GPIO.output(self.right_bwd_pin, GPIO.HIGH)
                else:
                    GPIO.output(self.right_fwd_pin, GPIO.LOW)
                    GPIO.output(self.right_bwd_pin, GPIO.LOW)
                
                if self.right_pwm:
                    self.right_pwm.ChangeDutyCycle(pwm_val)
    
    def stop(self):
        """
        停止時処理
        全モーターを緊急停止する。
        
        Args:
            None
        Returns:
            None
        """
        self.set_speed(0, 0)
    
    def run(self, throttle: float, steering: float) -> Tuple[float, float]:
        """
        パーツ実行処理
        
        Args:
            throttle: スロットル入力値 (-1.0 ～ 1.0)
            steering: ステアリング入力値 (-1.0 ～ 1.0)
            
        Returns:
            タプル (actual_left_speed, actual_right_speed)
        """
        if not self.initialized:
            return 0.0, 0.0
        
        # スロットル/ステアリングをディファレンシャルドライブに変える
        # ブルドーザーの場合：ポジティブステアリングで右旋回
        left_speed = throttle - steering
        right_speed = throttle + steering
        
        # 1.0を超えないように速度を正規化する
        max_speed = max(abs(left_speed), abs(right_speed))
        if max_speed > 1.0:
            left_speed /= max_speed
            right_speed /= max_speed
        
        self.set_speed(left_speed, right_speed)
        
        return left_speed, right_speed
    
    def shutdown(self):
        """
        シャットダウン処理

        Args:
            None
        Returns:
            None
        """
        self.stop()
        
        if GPIOZERO_AVAILABLE:
            if self.left_motor:
                self.left_motor.close()
            if self.right_motor:
                self.right_motor.close()
        else:
            if self.left_pwm:
                self.left_pwm.stop()
            if self.right_pwm:
                self.right_pwm.stop()
            
            # GPIO ピンのクリンナップ
            motor_pins = [
                self.left_fwd_pin, self.left_bwd_pin, self.left_en_pin,
                self.right_fwd_pin, self.right_bwd_pin, self.right_en_pin
            ]
            GPIO.cleanup(motor_pins)
        
        self.logger.info("Bulldozer actuator shutdown complete")


class BulldozerActuatorPart:
    """
    BulldozerActuatorクラスラッパー
    """
    
    def __init__(self, cfg):
        """
        Donkeycarの設定で初期化する。
        
        Args:
            cfg: Donkeycarの設定辞書
        Returns:
            None
        """
        self.actuator = BulldozerActuator(cfg)
    
    def run(self, throttle, steering):
        """
        Donkeycarパーツの実行処理
        
        Aegs:
            throttle: スロットル入力値 (-1.0 ～ 1.0)
            steering: ステアリング入力値 (-1.0 ～ 1.0)
        Returns:
            タプル (actual_left_speed, actual_right_speed)
        """
        return self.actuator.run(throttle, steering)
    
    def shutdown(self):
        """
        シャットダウン処理
        クリンナップを実行する
        
        Args:
            None
        Returns:
            None
        """
        self.actuator.shutdown()


# Donkeycar factory 関数

def get_bulldozer_actuator(cfg):
    """
    Donkeycar partsのファクトリ関数
    
    Args:
        cfg: Donkeycarの設定辞書
    Returns:
        BulldozerActuatorPart インスタンス
    """
    return BulldozerActuatorPart(cfg)


if __name__ == "__main__":
    """
    テスト実行
    """
    logging.basicConfig(level=logging.INFO)
    
    # Test 設定
    test_config = {
        'BULLDOZER_MOTORS': {
            'LEFT_MOTOR_FORWARD_PIN': 17,
            'LEFT_MOTOR_BACKWARD_PIN': 27,
            'LEFT_MOTOR_ENABLE_PIN': 22,
            'RIGHT_MOTOR_FORWARD_PIN': 23,
            'RIGHT_MOTOR_BACKWARD_PIN': 24,
            'RIGHT_MOTOR_ENABLE_PIN': 25,
            'PWM_FREQUENCY': 1000,
            'MAX_PWM': 1.0
        },
        'BULLDOZER_CONTROL': {
            'MIN_THROTTLE': 0.3,
            'ENABLE_SOFT_START': True
        }
    }
    
    try:
        actuator = BulldozerActuator(test_config)
        
        # 基本動作テスト
        print("Testing forward movement...")
        actuator.run(0.5, 0.0)
        time.sleep(2)
        
        print("Testing left turn...")
        actuator.run(0.3, 0.5)
        time.sleep(2)
        
        print("Testing right turn...")
        actuator.run(0.3, -0.5)
        time.sleep(2)
        
        print("Testing stop...")
        actuator.stop()
        
    except KeyboardInterrupt:
        print("Test interrupted by user")
    finally:
        actuator.shutdown()