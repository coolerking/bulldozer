#!/usr/bin/env python3
"""
Donkeycar用Nintendo Switch Bluetoothコントローラー

このモジュールは、Bluetooth Nintendo Switch対応コントローラーを使用してブルドーザーを制御するためのDonkeycarパーツを提供します。
Bluetooth経由でNintendo Switch Proコントローラーとジョイコンをサポートします。
"""

import logging
import time
import threading
import struct
from typing import Tuple, Optional, Dict, Any
from collections import namedtuple

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

try:
    import socket
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False

# コントローラー状態構造体
ControllerState = namedtuple('ControllerState', [
    'steering',      # -1.0 から 1.0
    'throttle',      # -1.0 から 1.0
    'button_a',      # Aボタン (×ボタン)
    'button_b',      # Bボタン (○ボタン)
    'button_x',      # Xボタン (□ボタン)
    'button_y',      # Yボタン (△ボタン)
    'button_l',      # Lボタン
    'button_r',      # Rボタン
    'button_zl',     # ZLボタン (左トリガー)
    'button_zr',     # ZRボタン (右トリガー)
    'button_minus',  # マイナスボタン
    'button_plus',   # プラスボタン
    'button_home',   # ホームボタン
    'button_capture', # キャプチャーボタン
    'dpad_up',       # 十字キー上
    'dpad_down',     # 十字キー下
    'dpad_left',     # 十字キー左
    'dpad_right',    # 十字キー右
    'left_stick_x',  # 左スティックX (-32768 から 32767)
    'left_stick_y',  # 左スティックY (-32768 から 32767)
    'right_stick_x', # 右スティックX (-32768 から 32767)
    'right_stick_y', # 右スティックY (-32768 から 32767)
    'connected'      # 接続状態
])

class SwitchController:
    """
    Nintendo Switch Bluetoothコントローラーインターフェース。
    
    Bluetooth経由でNintendo Switch Proコントローラーとジョイコンをサポートします。
    ブルドーザー制御用にコントローラー入力をステアリングとスロットルにマップします。
    """
    
    # Nintendo Switch Proコントローラーボタンマッピング
    SWITCH_BUTTONS = {
        'BTN_SOUTH': 'button_a',      # Aボタン
        'BTN_EAST': 'button_b',       # Bボタン
        'BTN_NORTH': 'button_x',      # Xボタン
        'BTN_WEST': 'button_y',       # Yボタン
        'BTN_TL': 'button_l',         # Lボタン
        'BTN_TR': 'button_r',         # Rボタン
        'BTN_TL2': 'button_zl',       # ZLボタン
        'BTN_TR2': 'button_zr',       # ZRボタン
        'BTN_SELECT': 'button_minus', # マイナスボタン
        'BTN_START': 'button_plus',   # プラスボタン
        'BTN_MODE': 'button_home',    # ホームボタン
        'BTN_THUMBL': 'button_capture', # キャプチャーボタン
    }
    
    SWITCH_HATS = {
        0: 'center',
        1: 'up',
        2: 'right',
        3: 'right-up',
        4: 'down',
        5: 'down-up',  # 無効
        6: 'down-right',
        7: 'down-right-up',  # 無効
        8: 'left',
        9: 'left-up',
        10: 'left-right',  # 無効
        11: 'left-right-up',  # 無効
        12: 'left-down',
        13: 'left-down-up',  # 無効
        14: 'left-down-right',
        15: 'left-down-right-up',  # 無効
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Switchコントローラーを初期化します。
        
        Args:
            config: コントローラー設定を含む設定辞書
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # コントローラー設定
        switch_config = config.get('SWITCH_CONTROLLER_CONFIG', {})
        self.device_file = config.get('JOYSTICK_DEVICE_FILE', '/dev/input/js0')
        self.bluetooth_timeout = switch_config.get('BLUETOOTH_TIMEOUT', 5.0)
        self.reconnect_attempts = switch_config.get('RECONNECT_ATTEMPTS', 3)
        self.enable_rumble = switch_config.get('ENABLE_RUMBLE', False)
        self.enable_motion = switch_config.get('ENABLE_MOTION', False)
        
        # 制御設定
        control_config = config.get('BULLDOZER_CONTROL', {})
        self.steering_scale = control_config.get('TURN_SENSITIVITY', 1.0)
        self.throttle_scale = config.get('JOYSTICK_MAX_THROTTLE', 0.8)
        self.deadzone = config.get('JOYSTICK_DEADZONE', 0.05)
        self.throttle_dir = config.get('JOYSTICK_THROTTLE_DIR', 1.0)
        
        # コントローラー状態
        self.device = None
        self.connected = False
        self.current_state = ControllerState(
            steering=0.0, throttle=0.0,
            button_a=False, button_b=False, button_x=False, button_y=False,
            button_l=False, button_r=False, button_zl=False, button_zr=False,
            button_minus=False, button_plus=False, button_home=False, button_capture=False,
            dpad_up=False, dpad_down=False, dpad_left=False, dpad_right=False,
            left_stick_x=0, left_stick_y=0, right_stick_x=0, right_stick_y=0,
            connected=False
        )
        
        # スレッド処理
        self._monitor_thread = None
        self._running = False
        self._lock = threading.Lock()
        
        # コントローラーに接続
        self.connect()
    
    def connect(self) -> bool:
        """Nintendo Switchコントローラーに接続します。"""
        try:
            if not EVDEV_AVAILABLE:
                self.logger.error("evdevライブラリが利用できません。次のコマンドでインストールしてください: pip3 install evdev")
                return False
            
            self.device = InputDevice(self.device_file)
            self.logger.info(f"{self.device.name} に {self.device.path} で接続しました")
            self.connected = True
            self.current_state = self.current_state._replace(connected=True)
            
            # 監視スレッドを開始
            self.start_monitoring()
            return True
            
        except FileNotFoundError:
            self.logger.error(f"{self.device_file} でコントローラーが見つかりません")
            self.connected = False
            self.current_state = self.current_state._replace(connected=False)
            return False
        except Exception as e:
            self.logger.error(f"コントローラーへの接続に失敗しました: {e}")
            self.connected = False
            self.current_state = self.current_state._replace(connected=False)
            return False
    
    def disconnect(self):
        """コントローラーから切断します。"""
        self.stop_monitoring()
        self.connected = False
        self.current_state = self.current_state._replace(connected=False)
        
        if self.device:
            self.device.close()
            self.device = None
    
    def start_monitoring(self):
        """バックグラウンドスレッドでコントローラー入力の監視を開始します。"""
        if not self.connected or self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("コントローラー監視を開始しました")
    
    def stop_monitoring(self):
        """コントローラー入力の監視を停止します。"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        self.logger.info("コントローラー監視を停止しました")
    
    def _monitor_loop(self):
        """コントローラー入力用のメイン監視ループ。"""
        while self._running and self.connected:
            try:
                # コントローラーイベントを読み取り
                for event in self.device.read_loop():
                    if not self._running:
                        break
                    
                    self._process_event(event)
                    
            except OSError as e:
                self.logger.error(f"コントローラーが切断されました: {e}")
                self.connected = False
                self.current_state = self.current_state._replace(connected=False)
                break
            except Exception as e:
                self.logger.error(f"コントローラーイベント処理中にエラーが発生しました: {e}")
                time.sleep(0.1)
    
    def _process_event(self, event):
        """単一のコントローラーイベントを処理します。"""
        if event.type == ecodes.EV_KEY:
            self._process_button_event(event)
        elif event.type == ecodes.EV_ABS:
            self._process_axis_event(event)
    
    def _process_button_event(self, event):
        """ボタンの押下/解放イベントを処理します。"""
        button_name = self._get_button_name(event.code)
        if button_name:
            value = bool(event.value)
            with self._lock:
                self.current_state = self.current_state._replace(**{button_name: value})
    
    def _process_axis_event(self, event):
        """アナログスティックの動きイベントを処理します。"""
        axis_name = self._get_axis_name(event.code)
        if axis_name:
            value = event.value
            with self._lock:
                self.current_state = self.current_state._replace(**{axis_name: value})
                self._update_steering_throttle()
    
    def _get_button_name(self, code):
        """evdevボタンコードを対応するボタン名にマップします。"""
        try:
            name = ecodes.BTN[code]
            return self.SWITCH_BUTTONS.get(name)
        except KeyError:
            return None
    
    def _get_axis_name(self, code):
        """evdev軸コードを対応する軸名にマップします。"""
        axis_map = {
            ecodes.ABS_X: 'left_stick_x',
            ecodes.ABS_Y: 'left_stick_y',
            ecodes.ABS_RX: 'right_stick_x',
            ecodes.ABS_RY: 'right_stick_y',
            ecodes.ABS_HAT0X: 'dpad_left',  # 十字キーは別途処理
            ecodes.ABS_HAT0Y: 'dpad_up',
        }
        return axis_map.get(code)
    
    def _update_steering_throttle(self):
        """現在のコントローラー状態からステアリングとスロットルを更新します。"""
        with self._lock:
            state = self.current_state
            
            # 主制御には左スティックを使用
            left_x = state.left_stick_x / 32768.0  # -1.0 から 1.0 に正規化
            left_y = state.left_stick_y / 32768.0  # -1.0 から 1.0 に正規化
            
            # デッドゾーンを適用
            left_x = self._apply_deadzone(left_x)
            left_y = self._apply_deadzone(left_y)
            
            # ステアリングとスロットルにマップ
            steering = left_x * self.steering_scale
            throttle = -left_y * self.throttle_scale * self.throttle_dir  # Y軸を反転
            
            # 十字キー制御を副入力として適用
            if state.dpad_left:
                steering = -1.0
            elif state.dpad_right:
                steering = 1.0
            
            if state.dpad_up:
                throttle = 1.0
            elif state.dpad_down:
                throttle = -1.0
            
            # 状態を更新
            self.current_state = state._replace(
                steering=steering,
                throttle=throttle
            )
    
    def _apply_deadzone(self, value: float) -> float:
        """アナログ入力にデッドゾーンを適用します。"""
        if abs(value) < self.deadzone:
            return 0.0
        
        # 残りの範囲をスケール
        if value > 0:
            return (value - self.deadzone) / (1.0 - self.deadzone)
        else:
            return (value + self.deadzone) / (1.0 - self.deadzone)
    
    def get_state(self) -> ControllerState:
        """現在のコントローラー状態を取得します。"""
        with self._lock:
            return self.current_state
    
    def is_connected(self) -> bool:
        """コントローラーが接続されているかチェックします。"""
        return self.connected
    
    def vibrate(self, intensity: float = 0.5, duration: float = 0.5):
        """コントローラーの振動をトリガーします（サポートされている場合）。"""
        if not self.enable_rumble or not self.connected:
            return
        
        # 注意: 振動サポートには追加の実装が必要です
        # これは将来の機能拡張用のプレースホルダーです
        self.logger.debug(f"振動が要求されました: intensity={intensity}, duration={duration}")


class SwitchControllerPart:
    """
    Nintendo Switch Controller用のDonkeycarパーツラッパー。
    """
    
    def __init__(self, cfg):
        """Donkeycar設定で初期化します。"""
        self.controller = SwitchController(cfg)
        self.logger = logging.getLogger(__name__)
        self.throttle = 0.0
        self.steering = 0.0
        self.recording = False
    
    def update(self):
        """コントローラー状態を更新します。"""
        if not self.controller.is_connected():
            # 再接続を試行
            self.controller.connect()
            return
        
        state = self.controller.get_state()
        self.throttle = state.throttle
        self.steering = state.steering
        
        # Aボタンで記録を処理
        self.recording = state.button_a
    
    def run(self, *args):
        """
        Donkeycarパーツインターフェース。
        
        Returns:
            (steering, throttle, recording)のタプル
        """
        self.update()
        return self.steering, self.throttle, self.recording
    
    def shutdown(self):
        """シャットダウン時のクリーンアップ。"""
        self.controller.disconnect()


class CustomJoystick:
    """
    Switch Controller用のDonkeycar互換ジョイスティックインターフェース。
    """
    
    def __init__(self, cfg):
        """ジョイスティックを初期化します。"""
        self.controller = SwitchController(cfg)
        self.throttle_scale = cfg.get('JOYSTICK_MAX_THROTTLE', 0.8)
        self.steering_scale = cfg.get('JOYSTICK_STEERING_SCALE', 1.0)
        self.auto_record = cfg.get('AUTO_RECORD_ON_THROTTLE', True)
        self.deadband = cfg.get('JOYSTICK_DEADZONE', 0.05)
    
    def init(self):
        """ジョイスティックを初期化します。"""
        return self.controller.connect()
    
    def poll(self):
        """コントローラーの入力をポーリングします。"""
        if not self.controller.is_connected():
            return None, None, None
        
        state = self.controller.get_state()
        
        # デッドバンドを適用
        steering = state.steering if abs(state.steering) > self.deadband else 0.0
        throttle = state.throttle if abs(state.throttle) > self.deadband else 0.0
        
        # 入力をスケール
        steering *= self.steering_scale
        throttle *= self.throttle_scale
        
        # 記録状態を決定
        recording = throttle != 0 or not self.auto_record
        
        return steering, throttle, recording
    
    def shutdown(self):
        """クリーンアップ。"""
        self.controller.disconnect()


# Donkeycarファクトリー関数

def get_switch_controller(cfg):
    """Donkeycarパーツ用のファクトリー関数。"""
    return SwitchControllerPart(cfg)

def get_custom_joystick(cfg):
    """Donkeycarカスタムジョイスティック用のファクトリー関数。"""
    return CustomJoystick(cfg)


if __name__ == "__main__":
    """Switchコントローラーのテストスクリプト。"""
    logging.basicConfig(level=logging.INFO)
    
    # テスト設定
    test_config = {
        'JOYSTICK_DEVICE_FILE': '/dev/input/js0',
        'JOYSTICK_MAX_THROTTLE': 0.8,
        'JOYSTICK_STEERING_SCALE': 1.0,
        'JOYSTICK_DEADZONE': 0.05,
        'AUTO_RECORD_ON_THROTTLE': True,
        'SWITCH_CONTROLLER_CONFIG': {
            'BLUETOOTH_TIMEOUT': 5.0,
            'RECONNECT_ATTEMPTS': 3,
            'ENABLE_RUMBLE': False,
            'ENABLE_MOTION': False
        }
    }
    
    try:
        controller = SwitchController(test_config)
        
        print("Switchコントローラーをテストしています...")
        print("スティックを動かしたりボタンを押したりして出力を確認してください")
        print("終了するにはCtrl+Cを押してください")
        
        while True:
            if controller.is_connected():
                state = controller.get_state()
                print(f"\rスロットル: {state.throttle:6.2f} | ステアリング: {state.steering:6.2f} | "
                      f"A:{state.button_a} B:{state.button_b} X:{state.button_x} Y:{state.button_y}", end='')
            else:
                print("\rコントローラーが切断されました。再接続を試行しています...", end='')
                controller.connect()
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nユーザーによってテストが中断されました")
    finally:
        controller.disconnect()