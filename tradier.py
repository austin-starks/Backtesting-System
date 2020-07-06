import requests
import os
import pandas as pd

api_key = os.environ['TRADIER_API_KEY']

trade_data_response = requests.get('https://sandbox.tradier.com/v1/markets/history?',
                                   params={'symbol': 'SPY200717P00320000',
                                           'start': '2020-06-01'},
                                   headers={'Authorization': api_key,
                                            'Accept': 'application/json'})
trade_data_json = trade_data_response.json()
trade_data_arr = trade_data_json['history']['day']
dates = []
trade_data = []
for element in trade_data_arr:
    dates.append(element['date'])
    trade_data.append([element['open'], element['high'],
                       element['low'], element['close'], element['volume']])
df = pd.DataFrame(trade_data, index=dates,
                  columns=["Open", "High", "Low", "Close", "Volume"])
print(df)
