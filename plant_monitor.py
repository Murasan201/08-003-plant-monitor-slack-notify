#!/usr/bin/env python3
"""
植物モニタリングシステム - ADS1015土壌水分センサー + Slack通知
要件: ads_1015_3_v_3_with_soil_sensor_notes.md
"""

import time
import datetime
import json
import requests
from board import SCL, SDA
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# 設定値（使用前に編集してください）
SLACK_WEBHOOK_URL = "YOUR_SLACK_WEBHOOK_URL_HERE"
MEASUREMENT_INTERVAL = 30 * 60  # 30分間隔（秒）

# センサー校正値（実際の環境に合わせて調整）
DRY_VALUE = 26000    # 乾燥時のセンサー値
WET_VALUE = 13000    # 湿潤時のセンサー値

def setup_sensor():
    """ADS1015センサーの初期化"""
    try:
        i2c = busio.I2C(SCL, SDA)
        ads = ADS.ADS1015(i2c)
        channel = AnalogIn(ads, ADS.P0)  # A0チャンネル使用
        return channel
    except Exception as e:
        print(f"センサー初期化エラー: {e}")
        return None

def read_soil_moisture(channel):
    """土壌水分を読み取り、パーセンテージに変換"""
    try:
        raw_value = channel.value
        voltage = channel.voltage

        # 0-100%に正規化
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
    """Slackに通知を送信"""
    if SLACK_WEBHOOK_URL == "YOUR_SLACK_WEBHOOK_URL_HERE":
        print("Slack WebHook URLが設定されていません")
        return False

    try:
        payload = {
            'text': message,
            'username': 'PlantBot',
            'icon_emoji': ':herb:'
        }

        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            print(f"Slack通知送信成功: {message}")
            return True
        else:
            print(f"Slack通知失敗: {response.status_code}")
            return False

    except Exception as e:
        print(f"Slack通知エラー: {e}")
        return False

def main():
    """メイン実行ループ"""
    print("植物モニタリングシステム開始")

    # センサー初期化
    sensor_channel = setup_sensor()
    if not sensor_channel:
        error_msg = "センサー初期化失敗 - プログラム終了"
        print(error_msg)
        send_slack_notification(f"🚨 エラー: {error_msg}")
        return

    print(f"30分間隔で監視開始（間隔: {MEASUREMENT_INTERVAL}秒）")

    try:
        while True:
            # 現在時刻
            now = datetime.datetime.now()
            timestamp = now.strftime('%Y-%m-%d %H:%M')

            # 土壌水分測定
            soil_data = read_soil_moisture(sensor_channel)

            if soil_data:
                # 通知メッセージ作成
                moisture = soil_data['moisture_percent']
                message = f"🌱 植物の土壌水分：{moisture}%（{timestamp}）"

                # コンソール出力
                print(f"測定結果 - 水分: {moisture}%, Raw: {soil_data['raw_value']}, 電圧: {soil_data['voltage']}V")

                # Slack通知
                send_slack_notification(message)

                # 水分が低い場合の追加警告
                if moisture < 30:
                    warning_msg = f"⚠️ 注意：土壌が乾燥しています（{moisture}%） - 水やりを検討してください"
                    send_slack_notification(warning_msg)

            else:
                error_msg = f"センサー読み取り失敗（{timestamp}）"
                print(error_msg)
                send_slack_notification(f"🚨 エラー: {error_msg}")

            # 次の測定まで待機
            print(f"次の測定まで{MEASUREMENT_INTERVAL}秒待機...")
            time.sleep(MEASUREMENT_INTERVAL)

    except KeyboardInterrupt:
        print("\nプログラム終了（Ctrl+Cが押されました）")
        send_slack_notification("🛑 植物モニタリングシステムを停止しました")
    except Exception as e:
        error_msg = f"予期しないエラー: {e}"
        print(error_msg)
        send_slack_notification(f"🚨 システムエラー: {error_msg}")

if __name__ == "__main__":
    main()