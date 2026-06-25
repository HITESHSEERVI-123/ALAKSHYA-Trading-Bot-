import pandas as pd
from datetime import datetime 
import time
from binance.client import Client 

api_key = "your_api_key"
secret_key = "your_secret_key"

client = Client(api_key, secret_key, testnet=True)

client.API_URL = "https://testnet.binancefuture.com"

csv_file = "bitcoin_data_history.csv"

try:
    status = client.futures_account()
    print("Connected! Account info fetched successfully.")
except Exception as e:
    print("Connection failed:", e)

while True:
    df = pd.read_csv(csv_file)
    
    if len(df) >= 3 :
        last_3_closes=df['close'].tail(3).astype(float)
        sma = last_3_closes.mean()
        last_close= float(df['close'].iloc[-1])
        print(f"last close{last_close},Sma is{sma}")

        if last_close>sma :
            print("signal buy")
            order = client.futures_create_order(
            symbol="ETHUSDT",
            side="BUY",
            type="MARKET",
            quantity=2
            )
            print(order)
        elif last_close<sma :
            print("signal sell")
            order = client.futures_create_order(
            symbol="ETHUSDT",
            side="SELL",
            type="MARKET",
            quantity=2            )
            print(order)
        elif last_close==sma :
            print("signal holding")
            

    else :
        print("not enough candles to fetch data")

    time.sleep(60)
    
    