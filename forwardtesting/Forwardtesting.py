import logging
import datetime
import pytz
import holidays
import os
import sys
import http.client
import json
import time
import pandas_datareader
import pandas as pd
import Conditions
import State


def load_stock_data(stock):
    if os.path.exists(f"price_data/{stock}.csv"):
        df = pd.read_csv(
            f"price_data/{stock}.csv", index_col="Date")
    else:
        df = pandas_datareader.data.DataReader(stock,
                                               start='2020-5-1',
                                               end=datetime.date.today().strftime("%m/%d/%Y"),
                                               data_source='yahoo')
        df.to_csv(f"price_data/{stock}.csv")
    return df


def get_stock_quote(connection, symbol):
    api_key = os.environ['TRADIER_API_KEY']
    headers = {"Accept": "application/json",
               "Authorization": api_key}
    connection.request(
        'GET', f'/v1/markets/quotes?symbols={symbol}', None, headers)
    try:
        response = connection.getresponse()
        content = response.read().decode("utf-8")
        my_json = json.loads(content)
        return my_json
    except http.client.HTTPException as e:
        print("Exception during request", e)
        return None


def market_is_open():
    tz = pytz.timezone('US/Eastern')
    us_holidays = holidays.US()
    now = datetime.datetime.now(tz)
    openTime = datetime.time(hour=9, minute=30, second=0)
    closeTime = datetime.time(hour=16, minute=0, second=0)
    abool = now.strftime('%Y-%m-%d') in us_holidays or now.time() < openTime or now.time() > closeTime \
        or now.date().weekday() > 4
    return not abool


def buy_or_sell(df, portfolio, price):
    buying_condition = Conditions.IsLowForPeriod(
        df, portfolio, 3, week_length=7)
    buying_condition.is_true('2020-07-10', price)
    print(df)


def forward_test(symbol):
    connection = http.client.HTTPSConnection(
        'sandbox.tradier.com', 443, timeout=30)
    df = load_stock_data(symbol)
    portfolio = State.Portfolio()
    while True:
        if not market_is_open():
            my_json = get_stock_quote(connection, symbol)
            price = my_json['quotes']['quote']['last']
            print('price', price)
            buy_or_sell(df, portfolio, price)
        else:
            print("Market is closed")
        time.sleep(3)


if __name__ == "__main__":
    # logging.basicConfig(
    #     filename=f'logs/{datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")}.log',
    #     format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    #     datefmt='%Y-%m-%d:%H:%M:%S',
    #     level=logging.INFO)

    forward_test("MSFT")
