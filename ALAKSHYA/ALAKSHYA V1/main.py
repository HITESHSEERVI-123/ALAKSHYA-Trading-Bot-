from binance.client import Client
from utils import fetching_account
import time
import datetime 

api_key = "your_api_key"
secret_key = "your_secret_key"

client = Client(api_key, secret_key, testnet=True)

client.API_URL = "https://testnet.binancefuture.com"

fetching_account(client=client)

#  this asks the file name for trade logs

while True:
    try:
        file_name = input("enter the file name (dont type the file type):")
        trade_logs = file_name + ".txt"
        break

    except FileNotFoundError:
        print("file not found so creating new file....")
        with open(trade_logs, "w") as w:
            pass

    except Exception as e :
        print(f"unexpected error:{e}")


while True:
    # this gets that the trade is placed or not 
     # Get positions safely
    positions = client.futures_position_information()
    amount = 0

    for pos in positions:
        if pos["symbol"] == "ETHUSDT":
            amount = float(pos["positionAmt"])
            break

    print("Position Amount:", amount)

    # If trade is already open, do nothing
    if amount != 0:
        print("Trade already open. Waiting...")
        time.sleep(5)
        continue


        # here we will check the indicators which will be done by v2 




        # the overall signal also done by v2 so let us assume the overall signal to buy is 1
    
    overall_signal = 1
        #  here we are placing trades
    if overall_signal>0:
        print("buying the trade")
        #  the sl and tp will be done in v2
        order = client.futures_create_order(symbol="ETHUSDT",
                                            side="BUY",
                                            type="MARKET",
                                            quantity=1)

        with open(trade_logs, "a") as a:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            a.write(f"{now} | BUY | ETHUSDT | Quantity: 1 | OrderID: {order['orderId']}\n")

        time.sleep(10)

    