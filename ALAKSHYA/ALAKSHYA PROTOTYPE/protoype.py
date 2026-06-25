import requests
import csv
import pandas as pd
import time


url="https://testnet.binance.vision/api/v3/klines"

params={"symbol":"ETHUSDT",
        "interval":"1m",
        "limit":1}

csv_file="bitcoin_data_history.csv"
with open(csv_file,mode="a+",newline="") as a:
    a.seek(0)
    content=a.read()
    writer=csv.writer(a)
    if content.strip() =="" :
        writer.writerow(["time", "open", "high", "low", "close", "volume"])

while True:

    raw_data=requests.get(url, params=params)
    data=raw_data.json()

    candle=data[0]

    new_row={"time": candle[0],
        "open": candle[1],
        "high": candle[2],
        "low": candle[3],
        "close": candle[4],
        "volume": candle[5]
        }
    
    df=pd.DataFrame([new_row])
    df.to_csv(csv_file, mode="a", index=False, header=False)

    print("Saved:", candle[0], candle[4])
    time.sleep(60)
    