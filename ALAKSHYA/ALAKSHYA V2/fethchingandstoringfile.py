import requests
import csv
import pandas as pd
import time
from utils import logs
from datetime import datetime
from indicators import (
    ema_indicator,
    rsi_indicator_smooth,
    volume_spike,
    macd_indicator,
    atr_indicator
)

def sync_with_csv():
    while True:
        now = datetime.now()
        if now.second == 0:
            break


URL = "https://testnet.binance.vision/api/v3/klines"
SYMBOL = "ETHUSDT"
INTERVAL = "1m"


# ================== CSV SETUP ==================

def initialize_csv(file_name):
    headers = [
        "time", "open", "high", "low", "close",
        "volume", "EMA", "VOLUME SPIKE", "RSI", "MACD", "ATR"
    ]

    try:
        with open(file_name, mode="a+", newline="") as f:
            f.seek(0)
            content = f.read().strip()
            if content == "":
                writer = csv.writer(f)
                writer.writerow(headers)
    except Exception as e:
        print("CSV init error:", e)
        logs(e)
        raise


# ================== GET CANDLE ==================

def fetch_latest_candle():
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": 1
    }

    try:
        response = requests.get(URL, params=params, timeout=10)
        data = response.json()

        if not isinstance(data, list) or not data:
            print("Bad response:", data)
            return None

        return data[-1]

    except Exception as e:
        print("Fetch error:", e)
        logs(e)
        return None


# ================== INDICATORS ==================

def calculate_indicators(df, volume):

    df = ema_indicator(df)
    ema_value = df["EMA"].iloc[-1] if "EMA" in df else None

    if len(df) >= 14:
        rsi_value = rsi_indicator_smooth(df)
    else:
        rsi_value = None

    volume_spike_value = volume_spike(df, volume)
    macd_value = macd_indicator(df)
    atr_value = atr_indicator(df)

    if isinstance(volume_spike_value, pd.DataFrame):
        volume_spike_value = volume_spike_value.iloc[-1, -1]

    if isinstance(macd_value, pd.DataFrame):
        macd_value = macd_value.iloc[-1, -1]

    if isinstance(atr_value, pd.DataFrame):
        atr_value = atr_value.iloc[-1, -1]

    if isinstance(rsi_value, pd.DataFrame):
        rsi_value = rsi_value.iloc[-1, -1]

    return ema_value, volume_spike_value, rsi_value, macd_value, atr_value


# ================== MAIN ==================

def main():

    file_name = input("Enter file name (no extension): ").strip()
    csv_file = file_name + ".csv"

    initialize_csv(csv_file)

    print(f"Started fetching for {SYMBOL} on {INTERVAL}")

    last_time = None  # avoid duplicate candle

    while True:

        sync_with_csv()
        candle = fetch_latest_candle()

        if candle is None:
            time.sleep(5)
            continue

        candle_time = candle[0]

        if candle_time == last_time:
            time.sleep(10)
            continue

        last_time = candle_time

        open_price = float(candle[1])
        high = float(candle[2])
        low = float(candle[3])
        close = float(candle[4])
        volume = float(candle[5])

        new_row = {
            "time": candle_time,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        }

        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            print("Read error:", e)
            logs(e)
            time.sleep(5)
            continue

        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        ema, v_spike, rsi, macd, atr = calculate_indicators(df, volume)

        final_row = {
            **new_row,
            "EMA": ema,
            "VOLUME SPIKE": v_spike,
            "RSI": rsi,
            "MACD": macd,
            "ATR": atr
        }

        try:
            pd.DataFrame([final_row]).to_csv(
                csv_file,
                mode="a",
                index=False,
                header=False
            )
            print("Saved:", candle_time, close)

        except Exception as e:
            print("Write error:", e)
            logs(e)

        time.sleep(60)


if __name__ == "__main__":
    main()
