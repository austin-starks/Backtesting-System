import requests
import os

api_key = os.environ['TRADIER_API_KEY']

trade_data_response = requests.get('https://sandbox.tradier.com/v1/markets/history?',
                                   params={'symbol': 'NVDA200710C00360000',
                                           'start': '2020-06-01'},
                                   headers={'Authorization': api_key,
                                            'Accept': 'application/json'}
                                   )
trade_data_json = trade_data_response.json()
print(trade_data_json['history']['day'][1])
