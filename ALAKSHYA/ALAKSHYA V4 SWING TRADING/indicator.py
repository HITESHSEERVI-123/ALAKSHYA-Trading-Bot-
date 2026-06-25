import pandas as pd
import ta

# ----------------- EMA -----------------
def calculate_emas(df):
    """
    Calculate EMA50, EMA200
    """
    df['EMA50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['EMA200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
    return df

# ----------------- VWAP -----------------
def calculate_vwap(df):
    """
    Calculate VWAP
    """
    df['VWAP'] = ta.volume.VolumeWeightedAveragePrice(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        volume=df['volume']
    ).volume_weighted_average_price()
    return df

# ----------------- ATR -----------------
def calculate_atr(df):
    """
    Calculate ATR(14) + ATR Mean (volatility filter)
    """
    atr = ta.volatility.AverageTrueRange(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=14
    ).average_true_range()

    df['ATR'] = atr
    df['ATR_MEAN'] = atr.rolling(50).mean()   # last ~50 candles volatility baseline
    return df

# ----------------- RSI -----------------
def calculate_rsi(df):
    """
    Calculate RSI(14)
    """
    df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    return df

# =============volumespike=================


def calculate_volume_spike(df, window=20, multiplier=1.5):
    """
    Volume Spike Logic (15M)

    window     = how many previous candles to average
    multiplier = how strong the spike must be

    Returns:
        True  -> volume spike present
        False -> normal volume
    """
    if len(df) < window:
        return False

    avg_volume = df['volume'].rolling(window).mean()
    current_volume = df['volume'].iloc[-1]

    return current_volume > (avg_volume.iloc[-1] * multiplier)

# ------------structure-------------
def calculate_structure(df_15m):
    if len(df_15m) < 3:
        return None

    # Simple logic: compare last 3 closes/highs/lows
    last = df_15m['close'].iloc[-1]
    prev = df_15m['close'].iloc[-2]
    prev2 = df_15m['close'].iloc[-3]

    # HH + HL = uptrend
    if prev2 < prev < last:
        return "HH+HL"
    # LL + LH = downtrend
    elif prev2 > prev > last:
        return "LL+LH"
    else:
        return None


# ----------------- Full calculation -----------------

def calculating_4h_indicators(df):
    df = calculate_emas(df)  # EMA50, EMA200
    # Return only the EMA values for storage
    return {
        "EMA50": df['EMA50'].iloc[-1],
        "EMA200": df['EMA200'].iloc[-1]
    }


def calculating_15m_indicators(df):
    df = calculate_atr(df)
    structure_value = calculate_structure(df)
    volume_spike = calculate_volume_spike(df)

    return {
        "ATR": df['ATR'].iloc[-1],
        "ATR_MEAN": df['ATR_MEAN'].iloc[-1],
        "STRUCTURE": structure_value,
        "VOLUME_SPIKE": volume_spike
    }

def calculating_5m_indicators(df):
    df = calculate_rsi(df)       # RSI
    df = calculate_vwap(df)      # VWAP
    # Also store the close price
    return {
        "RSI": df['RSI'].iloc[-1],
        "VWAP": df['VWAP'].iloc[-1]
    }

