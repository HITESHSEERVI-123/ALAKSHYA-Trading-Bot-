import pandas as pd


# ================= EMA =================

def ema_indicator(df, period=20):
    """
    Adds EMA column to dataframe
    """
    df["EMA"] = pd.to_numeric(df["close"], errors="coerce").ewm(
        span=period, adjust=False
    ).mean()

    return df


# ================= VOLUME SPIKE =================

def volume_spike(df, current_volume, multiplier=1.7):
    """
    Returns: True / False
    Checks if current volume is greater than (avg * multiplier)
    """

    if "volume" not in df or len(df) < 5:
        return False

    previous_volumes = pd.to_numeric(df["volume"], errors="coerce").dropna()

    if len(previous_volumes) == 0:
        return False

    avg_volume = previous_volumes.mean()
    threshold = avg_volume * multiplier

    return float(current_volume) > threshold


# ================= RSI =================

def rsi_indicator_smooth(df, period=14):
    """
    Adds RSI column and returns latest RSI value
    """

    if "close" not in df or len(df) < period:
        return None

    close = pd.to_numeric(df["close"], errors="coerce")

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))

    return float(df["RSI"].iloc[-1])


# ================= MACD =================

def macd_indicator(df, short_period=12, long_period=26, signal_period=9):
    """
    Adds MACD columns and returns latest MACD value
    """

    if "close" not in df or len(df) < long_period:
        return None

    close = pd.to_numeric(df["close"], errors="coerce")

    ema_short = close.ewm(span=short_period, adjust=False).mean()
    ema_long = close.ewm(span=long_period, adjust=False).mean()

    df["MACD"] = ema_short - ema_long
    df["MACD_Signal"] = df["MACD"].ewm(span=signal_period, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    return float(df["MACD"].iloc[-1])


# ================= ATR =================

def atr_indicator(df, period=14):
    """
    Adds ATR column and returns latest ATR value
    """

    if not {"high", "low", "close"}.issubset(df.columns) or len(df) < period:
        return None

    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce")

    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(period).mean()

    return float(df["ATR"].iloc[-1])
