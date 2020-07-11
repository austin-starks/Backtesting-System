import http.client
import os
import json

api_key = os.environ['TRADIER_API_KEY']
connection = http.client.HTTPSConnection(
    'sandbox.tradier.com', 443, timeout=30)

headers = {"Accept": "application/json",
           "Authorization": api_key}


connection.request(
    'GET', '/v1/markets/quotes?symbols=SHOP200717C01040000', None, headers)
try:
    response = connection.getresponse()
    content = response.read().decode("utf-8")
    my_json = json.loads(content)
    # Success
    print(my_json['quotes']['quote'], type(my_json))
    print('-------')
except http.client.HTTPException as e:
    # Exception
    print('Exception during request')

connection.request(
    'GET', '/v1/markets/quotes?symbols=SHOP', None, headers)

try:
    response = connection.getresponse()
    content = response.read().decode("utf-8")
    my_json = json.loads(content)
    # Success
    print(my_json['quotes']['quote'], type(my_json))
except http.client.HTTPException as e:
    # Exception
    print("Exception during request")
