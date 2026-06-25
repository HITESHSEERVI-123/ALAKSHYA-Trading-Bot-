import requests
import csv
import pandas as pd
import time
import os
from datetime import datetime
from utils import logs
from indicator import (
    calculating_4h_indicators,
    calculating_15m_indicators,
    calculating_5m_indicators
)

# ================= CONFIG =================
URL = "https://testnet.binance.vision/api/v3/klines"
SYMBOL = "ADAUSDT"
MAX_CANDLES = 500

CANDLE_FILES = {
    "4h": "4h_candle_data.csv",
    "15m": "15m_candle_data.csv",
    "5m": "5m_candle_data.csv"
}

# ================= FILE UTILITIES =================
def init_candle_csv(filename):
    if not os.path.exists(filename):
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "open", "high", "low", "close", "volume"])

def init_indicator_csv(filename):
    if not os.path.exists(filename):
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "EMA50", "EMA200",
                "ATR", "ATR_MEAN",
                "RSI", "VWAP", "STRUCTURE", "VOLUME_SPIKE"
            ])

def get_indicator_filename():
    name = input("Enter indicator CSV filename: ").strip()
    if not name.lower().endswith(".csv"):
        name += ".csv"
    return name

# ================= FETCH HISTORICAL =================
def fetch_historical_candles(symbol, interval, limit=MAX_CANDLES):
    try:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        r = requests.get(URL, params=params, timeout=10)
        data = r.json()
        if not isinstance(data, list) or len(data) < 2:
            return None
        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df = df[["time", "open", "high", "low", "close", "volume"]]
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        logs(e)
        print(f"Error fetching historical {interval} candles:", e)
        return None

# ================= CANDLE STORAGE =================
def store_candles(df, filename):
    if df is None or df.empty:
        return
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        old_df = pd.read_csv(filename)
        if not old_df.empty:
            df = pd.concat([old_df, df], ignore_index=True)
    df = df.tail(MAX_CANDLES)
    df.to_csv(filename, index=False)

# ================= INDICATOR STORAGE =================

def store_indicators(ind_data, filename):
    # normalize keys to avoid KeyError
    ind_4h = {k.upper(): v for k, v in ind_data["4h"].items()}
    ind_15m = {k.upper(): v for k, v in ind_data["15m"].items()}
    ind_5m = {k.upper(): v for k, v in ind_data["5m"].items()}

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ind_4h.get("EMA50", 0),
        ind_4h.get("EMA200", 0),
        ind_15m.get("ATR", 0),
        ind_15m.get("ATR_MEAN", 0),
        ind_5m.get("RSI", 0),
        ind_5m.get("VWAP", 0),
        ind_15m.get("STRUCTURE", "NONE"),
        ind_15m.get("VOLUME_SPIKE", False)
    ]

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)



# ================= INITIALIZATION =================
for f in CANDLE_FILES.values():
    init_candle_csv(f)

indicator_file = get_indicator_filename()
init_indicator_csv(indicator_file)

print("Initializing historical candle data...")
for tf, file in CANDLE_FILES.items():
    df_hist = fetch_historical_candles(SYMBOL, tf, limit=MAX_CANDLES)
    store_candles(df_hist, file)
print("Historical candle data ready")

# ================= LIVE LOOP =================
print("Starting live loop...")
while True:
    try:
        now = datetime.now()
        # Sleep until the start of the next minute
        time.sleep(60 - now.second - now.microsecond / 1_000_000)

        # Update candle files with latest closed candle
        for tf in CANDLE_FILES.keys():
            df_new = fetch_historical_candles(SYMBOL, tf, limit=2)
            store_candles(df_new.tail(1), CANDLE_FILES[tf])

        # Read stored candle data
        df_4h = pd.read_csv(CANDLE_FILES["4h"])
        df_15m = pd.read_csv(CANDLE_FILES["15m"])
        df_5m = pd.read_csv(CANDLE_FILES["5m"])

        # Calculate indicators
        ind_4h = calculating_4h_indicators(df_4h)
        ind_15m = calculating_15m_indicators(df_15m)  # should now include STRUCTURE + VOLUME_SPIKE
        ind_5m = calculating_5m_indicators(df_5m)

        store_indicators({
            "4h": ind_4h,
            "15m": ind_15m,
            "5m": ind_5m
        }, indicator_file)

        print("Saved candles + indicators @", datetime.now().strftime("%H:%M:%S"))

    except KeyboardInterrupt:
        print("Stopped by user")
        break
    except Exception as e:
        print("Loop error:", e)
        logs(e)
