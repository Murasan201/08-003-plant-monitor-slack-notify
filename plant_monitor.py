#!/usr/bin/env python3
"""
植物モニタリングシステム
Raspberry Pi 5 + ADS1015 + 容量式土壌水分センサーで植物の状態を監視し、Slackに通知します
要件定義書: ads_1015_3_v_3_with_soil_sensor_notes.md
"""

# 標準ライブラリ
import time
import datetime
import json

# サードパーティライブラリ
import requests
from board import SCL, SDA
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# 定数 - 使用前に編集してください
SLACK_WEBHOOK_URL = "YOUR_SLACK_WEBHOOK_URL_HERE"  # SlackのIncoming Webhook URL
MEASUREMENT_INTERVAL = 30 * 60  # 測定間隔（秒）: 30分ごと

# センサー校正値（実際の環境に合わせて調整してください）
# 校正方法: センサーを完全に乾燥させた状態でDRY_VALUE、水に浸した状態でWET_VALUEを測定
DRY_VALUE = 26000    # 乾燥時のセンサー値（ADC生値）
WET_VALUE = 13000    # 湿潤時のセンサー値（ADC生値）

def setup_sensor():
    """
    ADS1015センサーの初期化

    I²C通信でADS1015 ADコンバータに接続し、A0チャンネルを初期化します。
    ADS1015と土壌水分センサーは3.3V駆動で接続してください。

    Returns:
        AnalogIn: 初期化されたセンサーチャンネル（失敗時はNone）
    """
    try:
        # Raspberry PiのI²C通信を初期化（SCL/SDAピン使用）
        i2c = busio.I2C(SCL, SDA)

        # ADS1015を初期化（デフォルトI²Cアドレス: 0x48）
        ads = ADS.ADS1015(i2c)

        # A0チャンネルを使用（土壌水分センサー接続先）
        channel = AnalogIn(ads, ADS.P0)

        return channel
    except Exception as e:
        print(f"センサー初期化エラー: {e}")
        print("対処方法: 以下を確認してください")
        print("  - I²C設定が有効か確認: sudo raspi-config で I²C を有効化")
        print("  - デバイスが認識されているか確認: i2cdetect -y 1")
        print("  - 配線を確認: VCC→3.3V, GND→GND, SCL→SCL, SDA→SDA")
        return None

def read_soil_moisture(channel):
    """
    土壌水分を読み取り、パーセンテージに変換

    Args:
        channel (AnalogIn): ADS1015のアナログ入力チャンネル

    Returns:
        dict: 測定結果を含む辞書（失敗時はNone）
            - moisture_percent (float): 土壌水分率（0-100%）
            - raw_value (int): ADCの生値
            - voltage (float): 測定電圧（V）
    """
    try:
        # センサーの生値を読み取り（16bit ADCの値）
        raw_value = channel.value

        # 電圧値を取得（0-3.3V範囲）
        voltage = channel.voltage

        # 0-100%に正規化（DRY_VALUE=0%, WET_VALUE=100%として線形変換）
        # max/minで範囲外の値を0-100%に収める
        moisture_percent = max(0, min(100,
            ((DRY_VALUE - raw_value) / (DRY_VALUE - WET_VALUE)) * 100
        ))

        return {
            'moisture_percent': round(moisture_percent, 1),
            'raw_value': raw_value,
            'voltage': round(voltage, 3)
        }
    except Exception as e:
        print(f"センサー読み取りエラー: {e}")
        return None

def send_slack_notification(message):
    """
    Slackに通知を送信

    Args:
        message (str): 送信するメッセージ

    Returns:
        bool: 送信成功時はTrue、失敗時はFalse
    """
    # WebHook URLの設定確認
    if SLACK_WEBHOOK_URL == "YOUR_SLACK_WEBHOOK_URL_HERE":
        print("Slack WebHook URLが設定されていません")
        print("対処方法: SLACK_WEBHOOK_URL変数にWebHook URLを設定してください")
        return False

    try:
        # Slack通知用のペイロード作成
        payload = {
            'text': message,
            'username': 'PlantBot',      # 表示名
            'icon_emoji': ':herb:'       # アイコン（ハーブ）
        }

        # SlackのIncoming Webhook URLにPOSTリクエスト送信
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10  # タイムアウト10秒
        )

        # レスポンス確認
        if response.status_code == 200:
            print(f"Slack通知送信成功: {message}")
            return True
        else:
            print(f"Slack通知失敗: {response.status_code}")
            return False

    except Exception as e:
        print(f"Slack通知エラー: {e}")
        print("対処方法: インターネット接続とWebHook URLを確認してください")
        return False

def main():
    """
    メイン関数：センサーからデータを取得し、定期的にSlackへ通知

    30分間隔で土壌水分を測定し、Slackに通知します。
    水分が30%未満の場合は追加の警告メッセージを送信します。
    """
    print("植物モニタリングシステム開始")

    # センサーの初期化
    sensor_channel = setup_sensor()
    if not sensor_channel:
        error_msg = "センサー初期化失敗 - プログラム終了"
        print(error_msg)
        send_slack_notification(f"🚨 エラー: {error_msg}")
        return

    print(f"30分間隔で監視開始（間隔: {MEASUREMENT_INTERVAL}秒）")

    try:
        # 無限ループで定期測定
        while True:
            # 現在時刻を取得
            now = datetime.datetime.now()
            timestamp = now.strftime('%Y-%m-%d %H:%M')

            # 土壌水分を測定
            soil_data = read_soil_moisture(sensor_channel)

            if soil_data:
                # 測定成功時の処理
                moisture = soil_data['moisture_percent']
                message = f"🌱 植物の土壌水分：{moisture}%（{timestamp}）"

                # コンソールに詳細情報を出力
                print(f"測定結果 - 水分: {moisture}%, Raw: {soil_data['raw_value']}, 電圧: {soil_data['voltage']}V")

                # Slackに通知
                send_slack_notification(message)

                # 水分が低い場合の追加警告（30%未満）
                if moisture < 30:
                    warning_msg = f"⚠️ 注意：土壌が乾燥しています（{moisture}%） - 水やりを検討してください"
                    send_slack_notification(warning_msg)

            else:
                # 測定失敗時の処理
                error_msg = f"センサー読み取り失敗（{timestamp}）"
                print(error_msg)
                send_slack_notification(f"🚨 エラー: {error_msg}")

            # 次の測定まで待機
            print(f"次の測定まで{MEASUREMENT_INTERVAL}秒待機...")
            time.sleep(MEASUREMENT_INTERVAL)

    except KeyboardInterrupt:
        # Ctrl+Cでの中断処理
        print("\nプログラム終了（Ctrl+Cが押されました）")
        send_slack_notification("🛑 植物モニタリングシステムを停止しました")

    except Exception as e:
        # 予期しないエラーの処理
        error_msg = f"予期しないエラー: {e}"
        print(error_msg)
        send_slack_notification(f"🚨 システムエラー: {error_msg}")

if __name__ == "__main__":
    main()