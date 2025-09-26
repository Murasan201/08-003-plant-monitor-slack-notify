# 植物モニタリングシステム

ADS1015センサーで土壌水分を測定し、Slackに通知するシンプルなシステムです。

## 必要なもの

- Raspberry Pi 5
- ADS1015 ADコンバータ
- 容量式土壌水分センサー（3.3V駆動）
- Slack WebHook URL

## セットアップ

1. 依存関係をインストール：
```bash
pip install -r requirements.txt
```

2. `plant_monitor.py` でSlack WebHook URLを設定：
```python
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

3. センサー校正値を調整（必要に応じて）：
```python
DRY_VALUE = 26000    # 乾燥時の値
WET_VALUE = 13000    # 湿潤時の値
```

## 実行

```bash
python plant_monitor.py
```

30分ごとに土壌水分を測定し、Slackに通知します。

## 配線

- ADS1015のA0チャンネルに土壌水分センサーを接続
- I²C接続（SCL/SDA）でRaspberry Piと接続
- 電源は3.3Vを使用

## 停止

`Ctrl+C` でプログラムを停止できます。