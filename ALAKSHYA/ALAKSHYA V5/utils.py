import time
import pandas as pd
from datetime import datetime


# ================= LOGGING =================

def logs(message, file="logs.txt"):
    """
    Writes timestamped logs to file
    """
    readable_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{readable_time} | {str(message)}\n"

    try:
        with open(file, "a") as f:
            f.write(line)
    except Exception as e:
        print("Logging failed:", e)


# ================= CSV DATA HELPERS =================

def get_latest_column(file_name, column):
    """
    Returns the last value from a specific column
    """
    try:
        df = pd.read_csv(file_name)

        if len(df) == 0 or column not in df.columns:
            return None

        value = df[column].iloc[-1]
        return float(value) if pd.notna(value) else None

    except Exception as e:
        logs(e)
        return None


def get_last_second_column(file_name, column):
    """
    Returns second last value from a column
    """
    try:
        df = pd.read_csv(file_name)

        if len(df) < 2 or column not in df.columns:
            return None

        value = df[column].iloc[-2]
        return float(value) if pd.notna(value) else None

    except Exception as e:
        logs(e)
        return None


# ================= SAFE / PAPER TRADING =================

def fetching_account(client):
    try:
        account = client.futures_account()
        print("Demo account connected")
        return account
    except Exception as e:
        print("Account error:", e)
        return None



def place_trades(symbol, quantity, price=None, trade_type="BUY"):
    """
    Safe simulated trade
    NO REAL MONEY INVOLVED
    """

    open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    trade_data = {
        "symbol": symbol,
        "quantity": float(quantity),
        "side": trade_type,
        "price": price,
        "time": open_time,
        "status": "SIMULATED"
    }

    print("Simulated trade placed:", trade_data)
    logs(trade_data)

    return trade_data


# ================= OPEN POSITION CHECK (SIMULATED) =================

def check_open_position(trade_log="logs.txt", symbol=None):
    """
    Checks logs file for latest open simulated trade
    """

    try:
        with open(trade_log, "r") as f:
            lines = f.readlines()

        if not lines:
            return False, 0

        last = lines[-1]

        if symbol and symbol not in last:
            return False, 0

        # crude but effective for now
        if "SIMULATED" in last and "quantity" in last:
            qty = float(last.split("quantity': ")[1].split(",")[0])
            return True, qty

        return False, 0

    except Exception as e:
        logs(e)
        return False, 0


def fetch_closed_candle(SYMBOL, INTERVAL):
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": 2}

    try:
        response = requests.get(URL, params=params, timeout=10)
        data = response.json()

        if data is None:
            print("Data empty detected for interval:", INTERVAL)
            return None

        if not isinstance(data, list) or len(data) < 2:
            print(f"Bad response for {SYMBOL} at {INTERVAL}:", data)
            return None

        return data[0]   # Previous closed candle
    except Exception as e:
        print("Fetch error:", e)
        logs(e)
        return None

