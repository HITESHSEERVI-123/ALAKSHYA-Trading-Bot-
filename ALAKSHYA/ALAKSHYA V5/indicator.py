import pandas as pd
import ta

# ================= EMA =================
def calculate_emas(df, windows):
    """
    Calculate EMAs for given windows
    """
    for w in windows:
        df[f'EMA{w}'] = ta.trend.EMAIndicator(
            close=df['close'],
            window=w
        ).ema_indicator()
    return df


# ================= ATR =================
def calculate_atr(df, window=14, mean_window=50):
    """
    Calculate ATR and ATR_MEAN (volatility gate)
    """
    atr = ta.volatility.AverageTrueRange(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=window
    ).average_true_range()

    df['ATR'] = atr
    df['ATR_MEAN'] = atr.rolling(mean_window).mean()
    return df


# ========== 1H INDICATORS (BIAS) ==========
def calculate_1h_indicators(df_1h):
    df_1h = calculate_emas(df_1h, windows=[50, 200])

    return {
        "EMA50": df_1h['EMA50'].iloc[-1],
        "EMA200": df_1h['EMA200'].iloc[-1]
    }


# ========== 5M INDICATORS (ENTRY + VOL) ==========
def calculate_5m_indicators(df_5m):
    df_5m = calculate_emas(df_5m, windows=[9, 21])
    df_5m = calculate_atr(df_5m)

    return {
        "EMA9": df_5m['EMA9'].iloc[-1],
        "EMA21": df_5m['EMA21'].iloc[-1],
        "ATR": df_5m['ATR'].iloc[-1],
        "ATR_MEAN": df_5m['ATR_MEAN'].iloc[-1],
        "CLOSE": df_5m['close'].iloc[-1]
    }
