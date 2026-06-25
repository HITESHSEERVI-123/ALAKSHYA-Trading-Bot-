import requests
import csv
import pandas as pd
import time
import os
from datetime import datetime
from utils import logs
from indicator import (
    calculate_1h_indicators,
    calculate_5m_indicators
)

# ================= CONFIG =================
URL = "https://testnet.binance.vision/api/v3/klines"
SYMBOL = "ETHUSDT"
MAX_CANDLES = 500

CANDLE_FILES = {
    "1h": "1h_candle_data.csv",
    "5m": "5m_candle_data.csv"
}

INDICATOR_FILE = "indicators_v5.csv"

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
                "EMA9", "EMA21",
                "ATR", "ATR_MEAN",
                "CLOSE"
            ])

# ================= FETCH =================
def fetch_historical_candles(symbol, interval, limit=MAX_CANDLES):
    try:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        r = requests.get(URL, params=params, timeout=10)
        data = r.json()

        if not isinstance(data, list):
            return None

        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "trades",
            "tbb", "tbq", "ignore"
        ])

        df = df[["time", "open", "high", "low", "close", "volume"]]
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[
            ["open", "high", "low", "close", "volume"]
        ].apply(pd.to_numeric, errors="coerce")

        return df
    except Exception as e:
        logs(e)
        return None

# ================= STORE =================
def store_candles(df, filename):
    if df is None or df.empty:
        return

    if os.path.exists(filename):
        old = pd.read_csv(filename)
        frames = [x for x in [old, df] if x is not None and not x.empty]
        df = pd.concat(frames, ignore_index=True)


    df = df.tail(MAX_CANDLES)
    df.to_csv(filename, index=False)


def store_indicators(ind_1h, ind_5m, filename):
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ind_1h["EMA50"],
        ind_1h["EMA200"],
        ind_5m["EMA9"],
        ind_5m["EMA21"],
        ind_5m["ATR"],
        ind_5m["ATR_MEAN"],
        ind_5m["CLOSE"]
    ]

    with open(filename, "a", newline="") as f:
        csv.writer(f).writerow(row)

# ================= INIT =================
for f in CANDLE_FILES.values():
    init_candle_csv(f)

init_indicator_csv(INDICATOR_FILE)

print("Fetching historical candles...")
for tf, file in CANDLE_FILES.items():
    df = fetch_historical_candles(SYMBOL, tf)
    store_candles(df, file)

print("Historical data ready")

# ================= LIVE LOOP =================
print("Starting live loop...")
while True:
    try:
        now = datetime.now()
        time.sleep(60 - now.second)

        for tf, file in CANDLE_FILES.items():
            df_new = fetch_historical_candles(SYMBOL, tf, limit=2)
            store_candles(df_new.tail(1), file)

        df_1h = pd.read_csv(CANDLE_FILES["1h"])
        df_5m = pd.read_csv(CANDLE_FILES["5m"])

        ind_1h = calculate_1h_indicators(df_1h)
        ind_5m = calculate_5m_indicators(df_5m)

        store_indicators(ind_1h, ind_5m, INDICATOR_FILE)

        print("Saved indicators @", datetime.now().strftime("%H:%M:%S"))

    except KeyboardInterrupt:
        print("Stopped by user")
        break
    except Exception as e:
        logs(e)
