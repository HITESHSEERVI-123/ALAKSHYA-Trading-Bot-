import json 
import pandas
import requests
import time
from datetime import datetime
from binance.client import Client
from utils import fetching_account


api_key = "your_api_key"
secret_key = "your_secret_key"

client=Client(api_key, secret_key, testnet=True )

client.API_URL = "https://testnet.binancefuture.com"

account = fetching_account(client=client)

file_path = input("enter the name of file=")

  
# yaha pe sabse pehle if elif wala condition to check that is the trade is placed or not 
while True:
       

    try:
        with open(file_path, "r") as r:
            data = json.load(r)
            trade_history = data[-1]
            trade_status = trade_history.get("status")

    except FileNotFoundError:
        print("trades.json not found.")
        exit()
        

    except json.JSONDecodeError:
        print("Error decoding JSON. File might be corrupted.")
        exit()

    except Exception as e:
        print(f"unexpected error{e}")
        exit()

    if trade_status=="open":
        print("the trade is open so it will sleep until the trade hits the sl or tp...")
        time.sleep(2)

    elif trade_status=="close":
        
            #  yaha pe puchna hai ki agar status is closed then yaha pe andar indicators etc. rahege for making trades




                # sabse pehle dekhenge induicatoirs 
                #  ye jo kaam hai v2 main kiya jayega because the v2 is totally based on the indicators nad connecting to here 








                #  badme yaha pe overall signal batana hai 
                # this will also be done when the indicators will come but i am doing some part 
        overall_signal=1

        balance_info = client.futures_account_balance()

        usdt_balance = 0
        for asset in status["assets"]:
            if asset["asset"] == "USDT":
                usdt_balance = float(asset["walletBalance"])
                break

        print("Your USDT Balance:", usdt_balance)

        # Risk: 2 percent per trade
        risk_percent = 0.02  
        risk_amount = usdt_balance * risk_percent

        print("Risk amount per trade (2%):", risk_amount)

        price = float(client.futures_symbol_ticker(symbol="ETHUSDT")["price"])

        # convert risk amount to quantity
        quantity = risk_amount / price
        quantity = round(quantity, 3)  

        if overall_signal>0:
            order = client.futures_create_order(
            symbol="ETHUSDT",
            side="BUY",
            type="MARKET",
            quantity=quantity
            )
            print(f"the order is placed {quantity}")
            buying="buying the trade"
            print(buying)

            with open( file_path , "r") as file:
                trades = json.load(file)

            # Create new trade
            new_trade = {
                "trade_id": len(trades) + 1,  # auto-increment
                "symbol": "ETHUSDT",
                "side": "buy",
                "quantity": quantity,
                "price": price,
                "status": "open",
                "timestamp": datetime.now().isoformat()  # current time
            }

            # Add it to the list
            trades.append(new_trade)

            # Write back to JSON
            with open(file_path, "w") as file:
                json.dump(trades, file, indent=4)
                print("New trade added!")

        elif overall_signal==0:
            holding="holding"
            print("holding")

        else :
            print("the sign of selling but we are depending this on sl and tp ") 

                # saving the trades history


                # loop 

    else :
        print("invalid trade status found in json file ")
        exit()