import requests
import csv
import pandas as pd
import time
from utils import logs
from datetime import datetime
from indicators import *
from binance.client import Client

api_key = "your_api_key"
secret_key = "your_secret_key"

client = Client(API_KEY, SECRET_KEY)

URL = "https://testnet.binance.vision/api/v3/klines"   # Testnet
# URL = "https://api.binance.com/api/v3/klines"        # Real market

SYMBOL = "ETHUSDT"
INTERVAL = "1m"

# Column order (critical)
COLUMN_ORDER = [
    "time", "open", "high", "low", "close", "volume",
    "EMA50", "EMA200", "VWAP",
    "ATR", "ATR_MEAN", "RSI", "VOLUME SPIKE"
]

# ================== SYNC ==================


def sync_with_csv():
    now = datetime.now()
    
    # Calculate exactly how long to sleep until the next minute (XX:XX:00.0000)
    seconds_to_wait = 60 - now.second - (now.microsecond / 1_000_000)
    time.sleep(seconds_to_wait)
    print("syncing .........")
    # Add a small buffer (e.g., 0.5 seconds) to ensure the exchange API has finalized the minute's candle
    time.sleep(0.5) 
    
    # Place your CSV reading/saving logic here
    pass # Remove this 'pass' when you add your actual code

# ================== CSV SETUP ==================
def initialize_csv(file_name):
    try:
        with open(file_name, mode="a+", newline="") as f:
            f.seek(0)
            content = f.read().strip()
            if content == "":
                writer = csv.writer(f)
                writer.writerow(COLUMN_ORDER)
    except Exception as e:
        print("CSV init error:", e)
        logs(e)
        raise

# ================== FETCH LATEST CLOSED ==================
def fetch_closed_candle():
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": 2}

    try:
        response = requests.get(URL, params=params, timeout=10)
        data = response.json()

        if not isinstance(data, list) or len(data) < 2:
            print("Bad response:", data)
            return None

        return data[0]   # Previous closed candle
    except Exception as e:
        print("Fetch error:", e)
        logs(e)
        return None

# ================== WARM-UP FETCH ==================
def fetch_historical_and_warmup(limit=1000):
    try:
        klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=limit)

        df = pd.DataFrame(klines, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["time", "open", "high", "low", "close", "volume"]]
        return df

    except Exception as e:
        print("Historical fetch error:", e)
        logs(e)
        return None

# ================== EXTRACT LATEST INDICATORS ==================
def extract_latest_indicators(df):
    last_row = df.iloc[-1]

    v_spike = False
    if len(df) >= 20:
        vol_sma20 = df["volume"].rolling(20).mean().iloc[-1]
        v_spike = last_row["volume"] > vol_sma20

    return (
        last_row["EMA50"], last_row["EMA200"], last_row["VWAP"],
        last_row["ATR"], last_row["ATR_MEAN"], last_row["RSI"], v_spike
    )


# ================== MAIN ==================
def main():
    file_name = input("Enter file name (no extension): ").strip()
    csv_file = file_name + ".csv"
    initialize_csv(csv_file)

    # 1. WARM-UP
    print("Fetching historical data...")
    main_df = fetch_historical_and_warmup(1500)
    if main_df is None:
        return

    print("Calculating initial indicators...")
    main_df = calculate_all_indicators(main_df)
    main_df.dropna(inplace=True)
    main_df.reset_index(drop=True, inplace=True)

    # Add missing columns (like Volume Spike)
    for col in COLUMN_ORDER:
        if col not in main_df.columns:
            main_df[col] = None

    # Force correct order
    main_df = main_df.reindex(columns=COLUMN_ORDER)

    # Save warm-up history
    main_df.to_csv(csv_file, mode="a", index=False, header=False)
    last_processed_time = main_df["time"].iloc[-1]

    print(f"Warm-up complete. Last candle: {last_processed_time}")

    # 2. LIVE LOOP
    while True:
        sync_with_csv()

        raw_candle = fetch_closed_candle()
        if raw_candle is None:
            time.sleep(5)
            continue

        candle_time = raw_candle[0]

        if candle_time == last_processed_time:
            print("Candle already processed. Waiting...")
            time.sleep(10)
            continue

        new_row = {
            "time": candle_time,
            "open": float(raw_candle[1]),
            "high": float(raw_candle[2]),
            "low": float(raw_candle[3]),
            "close": float(raw_candle[4]),
            "volume": float(raw_candle[5])
        }

        # Add to RAM
        main_df = pd.concat([main_df, pd.DataFrame([new_row])], ignore_index=True)
        if len(main_df) > 1500:
            main_df = main_df.iloc[-1000:]

        # Indicators
        main_df = calculate_all_indicators(main_df)

        ema50, ema200, vwap, atr, atr_mean, rsi, v_spike = extract_latest_indicators(main_df)

        csv_row = {
            **new_row,
            "EMA50": ema50, "EMA200": ema200, "VWAP": vwap,
            "ATR": atr, "ATR_MEAN": atr_mean, "RSI": rsi, "VOLUME SPIKE": v_spike
        }


        # Save new row with fixed column order
        ordered_row = {col: csv_row.get(col) for col in COLUMN_ORDER}

        try:
            pd.DataFrame([ordered_row]).to_csv(csv_file, mode="a", index=False, header=False)
            print(f"[{datetime.now().time()}] Saved Candle: {candle_time}")
            last_processed_time = candle_time

        except Exception as e:
            print("Write error:", e)
            logs(e)

        time.sleep(30)

if __name__ == "__main__":
    main()

