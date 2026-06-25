import time
from binance.client import Client
import pandas as pd
from datetime import datetime


#  for storing the mainatanece of the autobot data 


def logs(log_text):
    ts = time.time()
    readable_time = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{readable_time} | {log_text}\n"
    
    with open("logs.txt", "a") as f:
        f.write(line)

#  to get the particular data of the particular column of the csv file

def get_columns(file_name, columns):
    try:
        df = pd.read_csv(file_name)
    except FileNotFoundError:
        print("File not found.")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    try:
        return df[columns]
    except KeyError:
        print("Column not found in CSV.")
        return None

# helps in fetching account 

def fetching_account(client):
    while True:
        try:
            status = client.futures_account()
            print("Connected! Account info fetched successfully.")
            return status
            break
        except Exception as e:
            print("Connection failed:", e)
            time.sleep(5)


# helps in placing trades
            
def place_trades(client, symbol, quantity): 
    try:
        print("buying the trade.....")
        open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order= client.futures_create_order(symbol=symbol,side="BUY",type="MARKET",quantity=quantity)
        print("trade placed succesfully ", (open_time))
        return order
    except Exception as e :
        print(f"unexpected error:{e}")

    
