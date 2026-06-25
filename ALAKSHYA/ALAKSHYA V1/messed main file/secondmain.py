import time
import json
from binance.client import Client
from datetime import datetime
from utils import fetching_account


api_key = "your_api_key"
secret_key = "your_secret_key"

client = Client(api_key, secret_key, testnet=True )

client.API_URL = "https://testnet.binancefuture.com"

fetching_account(client=client)

while True:
    file_path = input("enter the name of file(file type inculded):")
    if file_path.endswith(".json") :
        break

    else :
        print("you have entered invalid data type ")
        print("enter the file name which contains .json file type")

while True:
    try:
        try:
            with open(file_path , "r") as r:
                data = json.load(r)
        except:
            data = []

        if len(data)==0:
            print("no trades are there")
            status_of_trade = "close"
            latest_trade = {"trade_id": 0}

        else:
            latest_trade = data[-1]
            status_of_trade = latest_trade.get("status")
    
    except Exception as e:
        print(f"unexpected erro:{e}")

    if status_of_trade=="open":
        print("the trades status is open and waiting to hit sl or tp itslef")
        positions = client.futures_position_information(symbol="ETHUSDT")
        trades_history = positions[0]
        amount=float(trades_history.get("positionAmt"))

        if amount==0 :
            close_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry_price = float(latest_trade["price"])
            close_price = float(client.futures_symbol_ticker(symbol="ETHUSDT")["price"])
            pnl = close_price - entry_price

            price = float(client.futures_symbol_ticker(symbol="ETHUSDT")["price"])

            trades = {"trade_id": latest_trade["trade_id"],
            "symbol": "ETHUSDT",
            "side": latest_trade["side"],
            "quantity": latest_trade["quantity"],
            "price": latest_trade["price"],
            "status": "close",
            "pnl":pnl,
            "timestamp": close_time}
            
            data.append(trades)

            with open(file_path,"w") as w :
                json.dump(data, w, indent=4)

        elif amount!= 0 :
            time.sleep(5)

    elif status_of_trade=="close":
        #  here will come first the indicators will come and the overall signal calculated by it  
        overall_signal=1

        if overall_signal>0:
            print("buying the trade")
            open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            order= client.futures_create_order(symbol="ETHUSDT",side="BUY",type="MARKET",quantity=1)
            price = float(client.futures_symbol_ticker(symbol="ETHUSDT")["price"])

            trades = {"trade_id": latest_trade["trade_id"]+1,
            "symbol": "ETHUSDT",
            "side": "BUY",
            "quantity":1 ,
            "price": price ,
            "status": "open",
            "timestamp": open_time}
            data.append(trades)

            with open(file_path,"w") as w :
                json.dump(data, w, indent=4)

            time.sleep(10)

        elif overall_signal==0:
            print("holding trades")
    else :
        print("invalid error in json file")

