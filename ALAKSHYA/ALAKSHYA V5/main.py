import time
import pandas as pd
from datetime import datetime, timezone
from binance.client import Client

# ================== CONFIG =================
api_key = "your_api_key"
secret_key = "your_secret_key"
SYMBOL = "ETHUSDT"
LEVERAGE = 10
RISK_PER_TRADE = 0.01  # 1% per trade
MAX_TRADES_PER_SESSION = 3
MAX_LOSSES_PER_DAY = 2
COOLDOWN = 120  # seconds

SIDE_BUY = "BUY"
SIDE_SELL = "SELL"
ORDER_TYPE_MARKET = "MARKET"

# ================== FILES =================
TF_1H_CSV = "1h_candle_data.csv"
TF_5M_CSV = "5m_candle_data.csv"
INDICATOR_FILE = "indicators_v5.csv"

# ================== CLIENT =================
client = Client(API_KEY, SECRET_KEY, testnet=True)
client.API_URL = "https://testnet.binancefuture.com"
client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)

# ================== UTILS =================
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

# ================== SIGNAL =================
def read_signal():
    df = pd.read_csv(INDICATOR_FILE)
    if df.empty or len(df) < 1:
        print("Indicator file empty, skipping signal")
        return 0

    ind = df.iloc[-1]

    # 1H TREND BIAS
    ema50_1h = ind["EMA50"]
    ema200_1h = ind["EMA200"]
    if ema50_1h > ema200_1h:
        bias = "BUY"
    elif ema50_1h < ema200_1h:
        bias = "SELL"
    else:
        return 0

    # VOLATILITY FILTER (5M)
    if ind["ATR"] <= ind["ATR_MEAN"]:
        return 0

    # 5M PULLBACK ENTRY
    price = ind["CLOSE"]
    ema9 = ind["EMA9"]
    ema21 = ind["EMA21"]
    in_zone = min(ema9, ema21) <= price <= max(ema9, ema21)
    if not in_zone:
        return 0

    return 2 if bias == "BUY" else -2


# ================== SL / TP =================
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

# ================== MAIN =================
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

        if has_open_position():
            time.sleep(30)
            continue

        if trade_count >= MAX_TRADES_PER_SESSION or loss_count >= MAX_LOSSES_PER_DAY:
            print("Daily limits reached")
            time.sleep(300)
            continue

        signal = read_signal()
        if signal == 0:
            print(f"No trade signal at {datetime.now().strftime('%H:%M:%S')}")
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

        # --- MARKET ORDER ---
        try:
            order = client.futures_create_order(
                symbol=SYMBOL,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=qty
            )
            print(f"Market order executed. Order ID: {order['orderId']}")
        except Exception as e:
            print("Market order error:", e)
            time.sleep(60)
            continue

        # --- STOP LOSS ---
        try:
            client.futures_create_order(
                symbol=SYMBOL,
                side=close_side,
                type="STOP_MARKET",
                stopPrice=sl,
                closePosition=True
            )
            print("SL placed at", sl)
        except Exception as e:
            print("SL error:", e)

        # --- TAKE PROFIT ---
        try:
            client.futures_create_order(
                symbol=SYMBOL,
                side=close_side,
                type="TAKE_PROFIT_MARKET",
                stopPrice=tp,
                closePosition=True
            )
            print("TP placed at", tp)
        except Exception as e:
            print("TP error:", e)

        trade_count += 1
        time.sleep(COOLDOWN)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(60)
