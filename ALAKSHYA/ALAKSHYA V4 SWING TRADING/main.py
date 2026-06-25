import time
import pandas as pd
from datetime import datetime, timezone, time as dtime
from binance.client import Client
from binance.enums import *

api_key = "your_api_key"
secret_key = "your_secret_key"

# ================== CLIENT ==================
client = Client(API_KEY, SECRET_KEY, testnet=True)
client.API_URL = "https://testnet.binancefuture.com"
SYMBOL = "ETHUSDT"

client.futures_change_leverage(symbol=SYMBOL, leverage=10)

# ================== CONFIG ==================
MAX_TRADES_PER_SESSION = 3
MAX_LOSSES_PER_DAY = 2
RISK_PER_TRADE = 0.01      # 1%
COOLDOWN = 120

# ================== FILES ==================
TF_4H_CSV = "4h_candle_data.csv"
TF_15M_CSV = "15m_candle_data.csv"
TF_5M_CSV = "5m_candle_data.csv"
INDICATOR_FILE = "hitesh.csv"

# ================== SESSION FILTER ==================
def in_london_ny_session():
    now = datetime.now(timezone.utc).time()
    return dtime(12, 0) <= now <= dtime(17, 0)

# ================== UTILS ==================
def round_to_step(value, step):
    return round(round(value / step) * step, 8)

def get_equity():
    acc = client.futures_account()
    return float(acc["totalWalletBalance"])

def get_price():
    return float(client.futures_symbol_ticker(symbol=SYMBOL)["price"])

def has_open_position():
    positions = client.futures_position_information(symbol=SYMBOL)
    return any(float(p["positionAmt"]) != 0 for p in positions)

def get_symbol_filters():
    info = client.futures_exchange_info()
    for s in info["symbols"]:
        if s["symbol"] == SYMBOL:
            return s["filters"]

def get_lot_step():
    for f in get_symbol_filters():
        if f["filterType"] == "LOT_SIZE":
            return float(f["stepSize"])

def get_tick_size():
    for f in get_symbol_filters():
        if f["filterType"] == "PRICE_FILTER":
            return float(f["tickSize"])

# ================== SIGNAL (STRICT) ==================
def read_signal():
    df_4h = pd.read_csv(TF_4H_CSV)
    df_15m = pd.read_csv(TF_15M_CSV)
    df_5m = pd.read_csv(TF_5M_CSV)
    ind = pd.read_csv(INDICATOR_FILE).iloc[-1]

    c4h = df_4h.iloc[-1]
    c15 = df_15m.iloc[-1]
    c5 = df_5m.iloc[-1]

    # ---- 4H TREND ----
    ema50 = ind["EMA50"]
    ema200 = ind["EMA200"]
    close_4h = c4h["close"]

    trend_buy = ema50 > ema200 and close_4h > ema50
    trend_sell = ema50 < ema200 and close_4h < ema50
    if not (trend_buy or trend_sell):
        return 0

    # ---- 15M STRUCTURE + VOL ----
    if ind["ATR"] <= ind["ATR_MEAN"]:
        return 0
    if not bool(ind["VOLUME_SPIKE"]):
        return 0

    struct = ind["STRUCTURE"]
    if trend_buy and struct != "HH+HL":
        return 0
    if trend_sell and struct != "LL+LH":
        return 0

    # ---- 5M ENTRY ----
    open_, high, low, close = c5[["open", "high", "low", "close"]]
    vwap = ind["VWAP"]
    rsi = ind["RSI"]

    candle_range = high - low
    body = abs(close - open_)
    if candle_range == 0 or body < 0.5 * candle_range:
        return 0

    atr = ind["ATR"]

    pullback = (
        abs(close - vwap) <= 0.3 * atr
        or
        abs(close - ema50) <= 0.3 * atr
    )


    if not pullback:
        return 0

    if trend_buy and not (40 <= rsi <= 55):
        return 0
    if trend_sell and not (30 <= rsi <= 45):
        return 0

    return 2 if trend_buy else -2

# ================== SL / TP ==================
def calc_sl_tp(entry, side, atr, tick):
    sl_dist = atr * 1.5
    tp_dist = atr * 3

    if side == SIDE_BUY:
        sl = round_to_step(entry - sl_dist, tick)
        tp = round_to_step(entry + tp_dist, tick)
    else:
        sl = round_to_step(entry + sl_dist, tick)
        tp = round_to_step(entry - tp_dist, tick)

    return sl, tp, sl_dist

# ================== MAIN ==================
lot_step = get_lot_step()
tick_size = get_tick_size()

trade_count = 0
loss_count = 0
last_day = datetime.now(timezone.utc).date()

print("Bot started")

while True:
    try:
        today = datetime.now(timezone.utc).date()
        if today != last_day:
            trade_count = 0
            loss_count = 0
            last_day = today

        # if not in_london_ny_session():
        #     print("Outside session")
        #     time.sleep(60)
        #     continue

        if has_open_position():
            time.sleep(30)
            continue

        if trade_count >= MAX_TRADES_PER_SESSION or loss_count >= MAX_LOSSES_PER_DAY:
            print("Daily limits reached")
            time.sleep(300)
            continue

        signal = read_signal()
        if signal == 0:
            print(f"calculated overall signal:{signal}")
            time.sleep(60)
            continue

        side = SIDE_BUY if signal == 2 else SIDE_SELL
        close_side = SIDE_SELL if side == SIDE_BUY else SIDE_BUY

        entry = get_price()
        atr = pd.read_csv(INDICATOR_FILE).iloc[-1]["ATR"]

        sl, tp, sl_dist = calc_sl_tp(entry, side, atr, tick_size)

        equity = get_equity()
        risk_amount = equity * RISK_PER_TRADE
        raw_qty = risk_amount / sl_dist
        qty = round_to_step(raw_qty, lot_step)

        if qty <= 0:
            continue

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
        time.sleep(COOLDOWN)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(60)
