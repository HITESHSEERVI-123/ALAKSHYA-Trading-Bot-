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

# ================== CONFIG ==================
SYMBOL = "ETHUSDT"
QUANTITY = 10
STOP_LOSS_PERCENT = 0.5
TAKE_PROFIT_PERCENT = 1.0
MAX_TRADES = 5
COOLDOWN = 120  # seconds after a trade


# ================== FUNCTIONS ==================

def round_to_step(price, step):
    return round(round(price / step) * step, 8)

def sync_with_csv():
    """Synchronizes the bot to the start of the next full minute."""
    
    now = datetime.datetime.now()
    
    seconds_to_wait = 60 - now.second
    microsecond_adjustment = now.microsecond / 1000000.0
    
    sleep_time = seconds_to_wait - microsecond_adjustment

    if sleep_time <= 0:
        sleep_time += 60
    
    time.sleep(sleep_time)
    
    return
        

def read_signal(file_name: str) -> int:
    """
    Final version:
    BRAHMASHTRA decides IF trading is allowed.
    Then ANY ONE of these must confirm:
    EMA, VOLUME_SPIKE, RSI, MACD, ATR.
    
    Returns:
        2  = BUY
       -2  = SELL
        0  = HOLD
    """
    try:
        df = pd.read_csv(file_name)
        if df.empty:
            return 0

        latest = df.iloc[-1]

        # Required columns
        required = [
            "close", "EMA", "VOLUME_SPIKE", "RSI",
            "MACD", "ATR", "BRAHMASHTRA"
        ]

        for col in required:
            if col not in df.columns or pd.isna(latest[col]):
                return 0

        # Normalize brahmastra input
        b = str(latest["BRAHMASHTRA"]).upper().strip()

        # BRAHMASHTRA filter
        if b in ["NO_TRADE", "0", "NONE", "HOLD"]:
            return 0

        if b in ["1", "BUY", "BULLISH"]:
            b_signal = 1
        elif b in ["-1", "SELL", "BEARISH"]:
            b_signal = -1
        else:
            return 0

        # MAIN INDICATORS
        close = float(latest["close"])
        ema = float(latest["EMA"])
        rsi = float(latest["RSI"])
        macd = float(latest["MACD"])
        volume_spike = float(latest["VOLUME_SPIKE"])
        atr = float(latest["ATR"])

        # ----------------------------
        # CONFIRMATION CONDITIONS
        # ----------------------------

        # BUY confirmations
        confirm_buy = [
            close > ema,           # EMA Trend
            volume_spike > 1,      # Volume spike indicator (1 means spike detected)
            rsi < 70 and rsi > 40, # RSI mid-range bullish
            macd > 0,              # MACD bullish
            atr > 0                # ATR always > 0; depends how you define it
        ]

        # SELL confirmations
        confirm_sell = [
            close < ema,
            volume_spike < -1,     # Negative spike (your logic)
            rsi < 60 and rsi > 30, # RSI mid bearish
            macd < 0,
            atr > 0
        ]

        # ----------------------------
        # FINAL OUTPUT
        # ----------------------------
        if b_signal == 1:     # BUY
            if any(confirm_buy):
                return 2
            return 0

        if b_signal == -1:    # SELL
            if any(confirm_sell):
                return -2
            return 0

        return 0
        
    except Exception as e:
        print(f"Signal read error: {e}")
        return 0


# Note: The get_price function remains unchanged as it only fetches the price.
def get_price(client, SYMBOL):
    return float(client.futures_symbol_ticker(symbol=SYMBOL)["price"])


def get_price():
    return float(client.futures_symbol_ticker(symbol=SYMBOL)["price"])

def get_symbol_info():
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] == SYMBOL:
            return s
    return None

def calc_sl_tp(entry, side, step_price):
    if side == SIDE_BUY:
        sl = round_to_step(entry * (1 - STOP_LOSS_PERCENT / 100), step_price)
        tp = round_to_step(entry * (1 + TAKE_PROFIT_PERCENT / 100), step_price)
    else:
        sl = round_to_step(entry * (1 + STOP_LOSS_PERCENT / 100), step_price)
        tp = round_to_step(entry * (1 - TAKE_PROFIT_PERCENT / 100), step_price)
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
candle_file = input("Enter candle CSV file: ")
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

        if trade_count >= MAX_TRADES:
            print("Max trades reached. Exiting...")
            break

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
        sl, tp = calc_sl_tp(entry, side, tick_size)
        qty = round_to_step(QUANTITY, lot_step)

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

        position_info = client.futures_position_information(symbol=SYMBOL)[0]
        pos_amt = float(position_info['positionAmt'])

        if pos_amt > 0:
            position_side = "LONG"
        elif pos_amt < 0:
            position_side = "SHORT"
        else:
            position_side = None   # no position

                # Place SL
        client.futures_create_order(
            symbol=SYMBOL,
            side=client.SIDE_SELL if position_side=="LONG" else client.SIDE_BUY,
            type=client.ORDER_TYPE_STOP_MARKET,   # change to STOP_MARKET
            stopPrice=sl_price,
            closePosition=True,                   # crucial to attach to position
            reduceOnly=True
        )

        # Place TP
        client.futures_create_order(
            symbol=SYMBOL,
            side=client.SIDE_SELL if position_side=="LONG" else client.SIDE_BUY,
            type=client.ORDER_TYPE_TAKE_PROFIT_MARKET,  # change to TAKE_PROFIT_MARKET
            stopPrice=tp_price,
            closePosition=True,                   # crucial to attach to position
            reduceOnly=True
        )


        trade_count += 1
        print(f"Trade {trade_count}/{MAX_TRADES} executed. Cooling down {COOLDOWN}s...")
        time.sleep(COOLDOWN)

    except Exception as e:
        print("Main loop error:", e)
        time.sleep(60)
