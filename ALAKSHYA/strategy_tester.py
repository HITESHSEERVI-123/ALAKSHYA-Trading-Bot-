import pandas as pd

# ================== FILES =================
FILE_1H = "1h_candle_data.csv"
FILE_5M = "5m_candle_data.csv"

# ================== RISK =================
ATR_SL_MULT = 1.5
ATR_TP_MULT = 3.0

# ================== INDICATORS =================
def add_indicators(df):
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()

    # ATR
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    df['ATR_MEAN'] = df['ATR'].rolling(20).mean()

    return df

# ================== BACKTEST =================
def run_backtest():
    df1h = add_indicators(pd.read_csv(FILE_1H))
    df5m = add_indicators(pd.read_csv(FILE_5M))
    for df in (df1h, df5m):
        df['time'] = pd.to_datetime(df['time'])

    stats = {"trades": 0, "wins": 0, "pnl": 0.0}
    trade = None

    print("Backtest started (1H + 5M intraday)...")

    for i in range(200, len(df5m)):
        row5 = df5m.iloc[i]
        prev5 = df5m.iloc[i - 1]

        # ========== EXIT ==========  
        if trade:
            if trade["side"] == "BUY":
                if row5["low"] <= trade["sl"]:
                    stats["trades"] += 1
                    stats["pnl"] -= 1
                    trade = None
                elif row5["high"] >= trade["tp"]:
                    stats["trades"] += 1
                    stats["wins"] += 1
                    stats["pnl"] += 1.5
                    trade = None
            else:
                if row5["high"] >= trade["sl"]:
                    stats["trades"] += 1
                    stats["pnl"] -= 1
                    trade = None
                elif row5["low"] <= trade["tp"]:
                    stats["trades"] += 1
                    stats["wins"] += 1
                    stats["pnl"] += 1.5
                    trade = None
            continue

        # ========== SYNC 1H ==========
        try:
            row1 = df1h[df1h["time"] <= row5["time"]].iloc[-1]
        except IndexError:
            continue

        # ========== 1H TREND ==========
        trend_buy = row1["EMA50"] > row1["EMA200"]
        trend_sell = row1["EMA50"] < row1["EMA200"]

        if not (trend_buy or trend_sell):
            continue

        # ========== 5M VOLATILITY ==========
        if row5["ATR"] <= row5["ATR_MEAN"]:
            continue

        # ========== PULLBACK ENTRY ==========
        in_zone = min(row5["EMA9"], row5["EMA21"]) <= row5["close"] <= max(row5["EMA9"], row5["EMA21"])
        if not in_zone:
            continue

        # ========== STRUCTURE ==========
        structure_buy = row5["close"] > prev5["high"]
        structure_sell = row5["close"] < prev5["low"]

        # ========== ENTER TRADE ==========
        if trend_buy and structure_buy:
            trade = {
                "side": "BUY",
                "sl": row5["close"] - row5["ATR"] * ATR_SL_MULT,
                "tp": row5["close"] + row5["ATR"] * ATR_TP_MULT
            }
        elif trend_sell and structure_sell:
            trade = {
                "side": "SELL",
                "sl": row5["close"] + row5["ATR"] * ATR_SL_MULT,
                "tp": row5["close"] - row5["ATR"] * ATR_TP_MULT
            }

    wr = (stats["wins"] / stats["trades"] * 100) if stats["trades"] else 0

    print("\nFinal Stats")
    print("Trades:", stats["trades"])
    print("Wins:", stats["wins"])
    print(f"Win Rate: {wr:.2f}%")
    print("Total PnL (R):", stats["pnl"])

if __name__ == "__main__":
    run_backtest()
