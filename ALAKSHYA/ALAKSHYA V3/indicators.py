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

# ----------------- Volume -----------------
def calculate_volume(df):
    """
    Raw volume (no smoothing)
    """
    df['Volume'] = df['volume']
    return df

# ----------------- Full calculation -----------------
def calculate_all_indicators(df):
    df = calculate_emas(df)
    df = calculate_vwap(df)
    df = calculate_atr(df)
    df = calculate_rsi(df)
    df = calculate_volume(df)
    return df
