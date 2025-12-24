# セットアップガイド

植物モニタリングシステムの環境構築手順です。

## 必要なハードウェア

- Raspberry Pi 5
- ADS1015 ADコンバータ（I2Cアドレス: 0x48）
- 容量式土壌水分センサー
- ジャンパーワイヤー

## 配線

```
Raspberry Pi 5    ADS1015
--------------    -------
3.3V       --->   VDD
GND        --->   GND
GPIO2(SDA) --->   SDA
GPIO3(SCL) --->   SCL

ADS1015           土壌水分センサー
-------           ----------------
A0         --->   AOUT（アナログ出力）
VDD(3.3V)  --->   VCC
GND        --->   GND
```

## 1. I2Cの有効化

I2Cが有効になっているか確認します。

```bash
ls /dev/i2c-*
```

`/dev/i2c-1` が表示されればOKです。

表示されない場合は以下で有効化：

```bash
sudo raspi-config
# Interface Options > I2C > Yes を選択
sudo reboot
```

## 2. I2Cデバイスの確認

ADS1015が認識されているか確認します。

```bash
i2cdetect -y 1
```

アドレス `0x48` にデバイスが表示されればOKです。

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

## 3. 仮想環境の作成

```bash
cd /home/pi/work/project/08-003-plant-monitor-slack-notify
python3 -m venv venv
```

## 4. ライブラリのインストール

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### インストールされるライブラリ

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| requests | 2.32.5 | Slack通知用HTTPリクエスト |
| adafruit-circuitpython-ads1x15 | 3.0.2 | ADS1015 ADコンバータ制御 |
| adafruit-blinka | 8.68.1 | CircuitPython互換レイヤー |
| python-dotenv | 1.2.1 | 環境変数の読み込み |
| rpi-lgpio | 0.6 | Raspberry Pi 5 GPIO制御 |

## 5. Slack Webhook URLの設定

1. Slackで [Incoming Webhooks](https://api.slack.com/messaging/webhooks) を作成
2. `.env` ファイルを作成してWebhook URLを設定

```bash
# .envファイルを作成（このファイルはgit管理対象外）
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL" > .env
```

または手動で `.env` ファイルを作成：

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## 6. センサーの校正

センサーの個体差や環境により、校正値の調整が必要です。

### 6.1 現在のRaw値を確認

```bash
source venv/bin/activate
python3 -c "
from board import SCL, SDA
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(SCL, SDA)
ads = ADS.ADS1015(i2c)
channel = AnalogIn(ads, 0)
print(f'Raw値: {channel.value}')
print(f'電圧: {channel.voltage:.3f} V')
"
```

### 6.2 乾燥時の値を測定（DRY_VALUE）

センサーを空気中に置いた状態で上記コマンドを実行し、Raw値を記録します。

### 6.3 湿潤時の値を測定（WET_VALUE）

センサーを水に浸した状態で上記コマンドを実行し、Raw値を記録します。

### 6.4 校正値を更新

`plant_monitor.py` の以下の部分を実測値に更新します：

```python
DRY_VALUE = 17500    # 乾燥時のセンサー値（実測値に変更）
WET_VALUE = 7800     # 湿潤時のセンサー値（実測値に変更）
```

### 校正の実例

以下は実際の校正作業の例です：

| 状態 | Raw値 | 電圧 | 水分率 | 備考 |
|------|-------|------|--------|------|
| 乾燥（空気中） | 17557 | 2.192V | 0% | → DRY_VALUE = 17500 |
| 湿潤（水中） | 7810 | 0.974V | 100% | → WET_VALUE = 7800 |

**問題発生時の例**:

初期設定値 `DRY_VALUE = 26000` のまま使用した場合、センサーが空気中にあるのに水分率65.8%と表示されました。これは校正値が実際のセンサーと合っていなかったためです。

実測値 `DRY_VALUE = 17500` に修正後、水分率0%（乾燥状態）と正しく表示されるようになりました。

## 7. 動作確認

```bash
source venv/bin/activate
python plant_monitor.py
```

正常に動作すると以下が表示されます：

```
植物モニタリングシステム開始
30分間隔で監視開始（間隔: 1800秒）
測定結果 - 水分: 45.2%, Raw: 12500, 電圧: 1.560V
Slack通知送信成功: 植物の土壌水分：45.2%（2025-12-24 12:00）
次の測定まで1800秒待機...
```

## 8. 自動起動の設定（オプション）

systemdサービスとして登録する場合：

```bash
sudo nano /etc/systemd/system/plant-monitor.service
```

```ini
[Unit]
Description=Plant Monitoring System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/work/project/08-003-plant-monitor-slack-notify
ExecStart=/home/pi/work/project/08-003-plant-monitor-slack-notify/venv/bin/python plant_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable plant-monitor
sudo systemctl start plant-monitor
```

## トラブルシューティング

### センサーが認識されない

**現象**: プログラム実行時に「センサー初期化エラー」が表示される

**原因と対処**:

```bash
# I2Cデバイス確認
i2cdetect -y 1

# 配線を確認
# - VDD → 3.3V（5Vではない）
# - SDA → GPIO2
# - SCL → GPIO3
```

### lgpioモジュールが見つからない

**現象**: `ModuleNotFoundError: No module named 'lgpio'`

**原因**: Raspberry Pi 5では `rpi-lgpio` パッケージが必要

**対処**:
```bash
source venv/bin/activate
pip install rpi-lgpio
```

### Slack通知が送信されない

**現象**: 「Slack WebHook URLが設定されていません」と表示される

**原因と対処**:
- `.env` ファイルが存在するか確認
- Webhook URLが正しく設定されているか確認
- インターネット接続を確認
- `curl` でテスト:

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"テスト"}' \
  YOUR_WEBHOOK_URL
```

### 水やり後なのに水分値が下がった

**現象**: 水やり直後なのに水分率が下がる（例: 36% → 21%）

**原因**: センサーが湿った土に接触していない

**対処**:
1. センサーを土の奥までしっかり差し込む
2. センサー付近に直接水をかける
3. センサー周りの土が湿っていることを確認

### 水分値が不正確（乾燥しているのに高い値が出る）

**現象**: センサーが空気中にあるのに水分率が50%以上と表示される

**原因**: 校正値（DRY_VALUE / WET_VALUE）がセンサーの実測値と合っていない

**対処**: `plant_monitor.py` の校正値を実測値に調整

```python
DRY_VALUE = 17500    # 完全乾燥時の値（実測）
WET_VALUE = 8000     # 水浸し時の値（実測）
```

**校正手順**:

1. センサーのRaw値を確認するテストコードを実行:

```bash
source venv/bin/activate
python3 -c "
from board import SCL, SDA
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(SCL, SDA)
ads = ADS.ADS1015(i2c)
channel = AnalogIn(ads, 0)
print(f'Raw値: {channel.value}')
print(f'電圧: {channel.voltage:.3f} V')
"
```

2. センサーを空気中に置き、Raw値を確認 → `DRY_VALUE` に設定
3. センサーを水に浸し、Raw値を確認 → `WET_VALUE` に設定
4. `plant_monitor.py` の値を更新
