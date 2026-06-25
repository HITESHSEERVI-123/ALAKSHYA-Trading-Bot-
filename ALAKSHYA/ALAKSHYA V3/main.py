import time
import pandas as pd
from datetime import datetime
from binance.client import Client
from binance.enums import *

api_key = "your_api_key"
secret_key = "your_secret_key"

# ================== CLIENT ==================  
client = Client(API_KEY, SECRET_KEY, testnet=True)
client.API_URL = "https://testnet.binancefuture.com"
SYMBOL = "ETHUSDT"

try:
    client.futures_change_leverage(symbol=SYMBOL, leverage=10)
    print("Leverage set to 10x")
except Exception as e:
    print("Failed to set leverage:", e)

# ================== CONFIG ==================
QUANTITY = 5
STOP_LOSS_PERCENT = 0.5
TAKE_PROFIT_PERCENT = 1.0
MAX_TRADES = 5
COOLDOWN = 120  # seconds after a trade

# ================== FUNCTIONS ==================

def round_to_step(price, step):
    return round(round(price / step) * step, 8)


def sync_with_csv():
    now = datetime.now()
    
    # Calculate exactly how long to sleep until the next minute (XX:XX:00.0000)
    seconds_to_wait = 60 - now.second - (now.microsecond / 1_000_000)
    time.sleep(seconds_to_wait)
    print("syncing.........")
    # Add a small buffer (e.g., 0.5 seconds) to ensure the exchange API has finalized the minute's candle
    time.sleep(1) 
    
    # Place your CSV reading/saving logic here
    pass # Remove this 'pass' when you add your actual code


def read_signal(file_name: str) -> int:
    try:
        df = pd.read_csv(file_name)
        if df.empty:
            return 0

        latest = df.iloc[-1]

        # New required columns
        required = [
            "close", "EMA50", "EMA200", "VWAP",
            "ATR", "ATR_MEAN", "RSI", "VOLUME SPIKE",
            "STRUCTURE"  # Ensure you have structure column HH+HL or LL+LH
        ]
        for col in required:
            if col not in df.columns or pd.isna(latest[col]):
                return 0

        # Latest values
        close = float(latest["close"])
        ema50 = float(latest["EMA50"])
        ema200 = float(latest["EMA200"])
        vwap = float(latest["VWAP"])
        atr = float(latest["ATR"])
        atr_mean = float(latest["ATR_MEAN"])
        rsi = float(latest["RSI"])
        volume_spike = bool(latest["VOLUME SPIKE"])
        structure = latest["STRUCTURE"]

        # ----------------------------
        # CONFIRMATION CONDITIONS
        # ----------------------------

        # EMA confirmation
        ema_buy = ema50 > ema200 and close > ema50
        ema_sell = ema50 < ema200 and close < ema50

        # RSI confirmation
        rsi_buy = 40 < rsi < 55
        rsi_sell = 45 > rsi > 30  # adjusted for scalping momentum reset

        # ATR filter (volatility baseline)
        atr_ok = atr > atr_mean

        # Structure confirmation
        struct_buy = structure == "HH+HL"
        struct_sell = structure == "LL+LH"

        # Volume Spike confirmation
        vol_ok = volume_spike

        # ----------------------------
        # FINAL DECISION
        # ----------------------------
        # Only enter if ALL filters match for BUY or SELL
        if all([ema_buy, atr_ok, rsi_buy, struct_buy, vol_ok]):
            return 2  # BUY
        elif all([ema_sell, atr_ok, rsi_sell, struct_sell, vol_ok]):
            return -2  # SELL

        return 0  # HOLD

    except Exception as e:
        print(f"Signal read error: {e}")
        return 0


def get_price():
    return float(client.futures_symbol_ticker(symbol=SYMBOL)["price"])

def get_symbol_info():
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] == SYMBOL:
            return s
    return None

def calc_sl_tp(entry, side, atr_value, step_price):
    """
    ATR-based Stop Loss and Take Profit for scalping
    Stop Loss = 1.5 × ATR
    Take Profit = 3 × ATR (RR 1:2)
    """
    sl_dist = atr_value * 1.5
    tp_dist = atr_value * 3.0
    
    if side == SIDE_BUY:
        sl = round_to_step(entry - sl_dist, step_price)
        tp = round_to_step(entry + tp_dist, step_price)
    else:
        sl = round_to_step(entry + sl_dist, step_price)
        tp = round_to_step(entry - tp_dist, step_price)
        
    return sl, tp

def has_open_position():
    positions = client.futures_position_information(symbol=SYMBOL)
    for pos in positions:
        if float(pos['positionAmt']) != 0:
            return True, float(pos['positionAmt'])
    return False, 0

def get_lot_step():
    info = get_symbol_info()
    for f in info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            return float(f['stepSize'])
    return 1

def get_tick_size():
    info = get_symbol_info()
    for f in info['filters']:
        if f['filterType'] == 'PRICE_FILTER':
            return float(f['tickSize'])
    return 0.01

# ================== MAIN ==================
def get_csv_filename(prompt="Enter CSV filename: "):
    """
    Prompts user for a CSV filename, ensures it ends with .csv,
    and checks basic validity.
    Returns the valid filename.
    """
    while True:
        try:
            filename = input(prompt).strip()
            
            # Ensure it ends with .csv
            if not filename.lower().endswith(".csv"):
                print("Filename must end with .csv. Adding automatically.")
                filename += ".csv"
            
            # Optional: Try opening file in append mode to check write permission
            try:
                with open(filename, 'a', newline='') as f:
                    pass
            except Exception as e:
                print(f"Cannot access file '{filename}': {e}")
                continue
            
            return filename
        
        except KeyboardInterrupt:
            print("\nInput cancelled by user.")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}. Try again.")

filename = get_csv_filename()
if filename:
    print("CSV file ready to use:", filename)
else:
    print("No file provided. Exiting.")


trade_count = 0
lot_step = get_lot_step()
tick_size = get_tick_size()
last_signal_time = None

print("Bot started...")

while True:
    try:
        # Check open position
        open_pos, amt = has_open_position()
        if open_pos:
            print(f"Open position detected: {amt}. Waiting...")
            time.sleep(60)
            continue

        # if trade_count >= MAX_TRADES:
        #     print("Max trades reached. Exiting...")
        #     break

        sync_with_csv()

        df = pd.read_csv(candle_file)
        latest_time = df.iloc[-1]["time"] if "time" in df.columns else None
        if latest_time == last_signal_time:
            print("No new candle yet. Waiting...")
            time.sleep(10)
            continue
        last_signal_time = latest_time

        signal = read_signal(candle_file)
        print("Signal:", signal)
        if signal == 0:
            print("No trade. Waiting...")
            time.sleep(60)
            continue

        side = SIDE_BUY if signal == 2 else SIDE_SELL
        opposite = SIDE_SELL if side == SIDE_BUY else SIDE_BUY

        entry = get_price()
        latest_df = pd.read_csv(candle_file)
        atr_value = float(latest_df.iloc[-1]["ATR"])
        sl, tp = calc_sl_tp(entry, side, atr_value, tick_size)
        min_notional = 20
        raw_qty = min_notional / entry

        # make sure qty is NOT reduced by rounding
        # qty = ((raw_qty // lot_step) * lot_step)
        # if qty < raw_qty:
        #     qty += lot_step
        # qty = round(qty, 8)
        qty = QUANTITY

        print(f"ENTRY: {entry} | SL: {sl} | TP: {tp} | QTY: {qty}")

        # MARKET ORDER
        try:
            order = client.futures_create_order(
                symbol=SYMBOL,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=qty
            )
            order_id = order['orderId']
            print(f"Market order executed. Order ID: {order_id}")
        except Exception as e:
            print("Market order error:", e)
            time.sleep(60)
            continue

        CLOSING_SIDE = SIDE_SELL if side == SIDE_BUY else SIDE_BUY

        # --- STOP LOSS (MARKET) ---
        # --- STOP LOSS ---
        try:
            sl_order = client.futures_create_order(
                symbol=SYMBOL,
                side=CLOSING_SIDE,
                type="STOP_MARKET",
                stopPrice=sl,
                closePosition=True
            )
            print("SL order response:", sl_order)
        except Exception as e:
            print("SL order error:", e)

        # --- TAKE PROFIT ---
        try:
            tp_order = client.futures_create_order(
                symbol=SYMBOL,
                side=CLOSING_SIDE,
                type="TAKE_PROFIT_MARKET",
                stopPrice=tp,
                closePosition=True
            )
            print("TP order response:", tp_order)
        except Exception as e:
            print("TP order error:", e)

        trade_count += 1
        print(f"Trade {trade_count}/{MAX_TRADES} executed. Cooling down {COOLDOWN}s...")
        time.sleep(COOLDOWN)

    except Exception as e:
        print("Main loop error:", e)
        time.sleep(60)
