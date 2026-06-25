import time
import pandas as pd
from binance.client import Client
from binance.enums import *
from datetime import datetime 
from utils import fetching_account, check_open_position, logs


# ================== CONFIG ==================

api_key = "your_api_key"
secret_key = "your_secret_key"


SYMBOL = "ETHUSDT"
QUANTITY = 10

STOP_LOSS_PERCENT = 0.5
TAKE_PROFIT_PERCENT = 1.0

MAX_TRADES = 5


# ================== CLIENT ==================

client = Client(API_KEY, SECRET_KEY, testnet=True)
client.API_URL = "https://testnet.binancefuture.com"


# ================== FUNCTIONS ==================


def sync_with_csv():
    while True:
        now = datetime.now()
        if now.second == 2:
            break


# Usage
def read_and_confirm_indicators(file_name: str) -> int:
    try:
        df = pd.read_csv(file_name)

        if df.empty:
            print("CSV is empty")
            return 0

        latest = df.iloc[-1]

        required_cols = ["RSI", "MACD", "EMA", "close"]
        for col in required_cols:
            if col not in df.columns or pd.isna(latest[col]):
                print(f"Missing or invalid column: {col}")
                return 0

        rsi = latest["RSI"]
        macd = latest["MACD"]
        ema = latest["EMA"]
        close = latest["close"]

        # ----- Weighted scoring -----
        score = 0

        # EMA Trend
        if close > ema:
            score += 1
        elif close < ema:
            score -= 1

        # RSI Momentum
        if rsi > 55:
            score += 1
        elif rsi < 45:
            score -= 1

        # MACD Confirmation
        if macd > 0:
            score += 1
        elif macd < 0:
            score -= 1

        # Volume Spike (optional, half weight)
        if "VOLUME SPIKE" in df.columns:
            if str(latest["VOLUME SPIKE"]).lower() == "true":
                score += 0.5
            else:
                score -= 0.5

        # ----- Decision thresholds -----
        if score >= 2.5:
            return 2    # BUY
        elif score <= -2.5:
            return -2   # SELL
        else:
            return 0    # HOLD

    except Exception as e:
        print(f"Indicator processing error: {e}")
        logs(e)
        return 0




def get_latest_price():
    ticker = client.futures_symbol_ticker(symbol=SYMBOL)
    return float(ticker["price"])


def calculate_sl_tp(entry_price, side):
    if side == SIDE_BUY:
        sl = entry_price * (1 - STOP_LOSS_PERCENT / 100)
        tp = entry_price * (1 + TAKE_PROFIT_PERCENT / 100)

    else:
        sl = entry_price * (1 + STOP_LOSS_PERCENT / 100)
        tp = entry_price * (1 - TAKE_PROFIT_PERCENT / 100)

    return round(sl, 2), round(tp, 2)


# ================== FILE INPUT ==================

def get_valid_file(prompt, extension):
    while True:
        name = input(prompt)
        if name.endswith(extension):
            try:
                with open(name, "r"):
                    return name
            except FileNotFoundError:
                print("File does not exist.")
                logs("File not found: " + name)


candle_file = get_valid_file("Enter candle file (.csv): ", ".csv")
trade_logs = get_valid_file("Enter trade log file (.txt): ", ".txt")


# ================== START ==================

fetching_account(client)
trade_count = 0

print("Bot started...")


while True:
    try:
        has_position, position_amt = check_open_position(client, SYMBOL)

        if has_position:
            print(f"Open position found: {position_amt}")
            time.sleep(60)
            sync_with_csv()
            continue

        if trade_count >= MAX_TRADES:
            print("Daily limit reached. exiting the program...")
            exit()

        sync_with_csv()
        signal = read_and_confirm_indicators(candle_file)
        print(f"Signal: {signal}")

        # ---- HANDLE SIGNAL ----
        if signal == 2:
            side = SIDE_BUY
            opposite = SIDE_SELL

        elif signal == -2:
            side = SIDE_SELL
            opposite = SIDE_BUY

        else:
            print("Hold signal. No trade.")
            time.sleep(60)
            sync_with_csv()
            continue

        # ---- ENTRY / SL / TP ----
        entry = get_latest_price()
        sl, tp = calculate_sl_tp(entry, side)

        print(f"ENTRY: {entry} | SL: {sl} | TP: {tp}")

        # ----- MARKET ORDER -----
        client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type=FUTURE_ORDER_TYPE_MARKET,
            quantity=QUANTITY
        )

        print("Market order placed")


        # ----- STOP LOSS -----
        client.futures_create_order(
            symbol=SYMBOL,
            side=opposite,
            type=FUTURE_ORDER_TYPE_STOP_MARKET,
            stopPrice=sl,
            closePosition=True,
            timeInForce=TIME_IN_FORCE_GTC
        )

        print("Stop loss set")

        # ----- TAKE PROFIT -----
        client.futures_create_order(
            symbol=SYMBOL,
            side=opposite,
            type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=tp,
            closePosition=True,
            timeInForce=TIME_IN_FORCE_GTC
        )

        print("Take profit set")

        trade_count += 1
        print(f"Trade {trade_count}/{MAX_TRADES} executed")

        # Cooldown after a trade
        time.sleep(120)
        sync_with_csv()
       

    except Exception as e:
        print(f"Main loop error: {e}")
        logs(e)
        time.sleep(60)
        
        
