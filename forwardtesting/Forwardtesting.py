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


class ForwardTesting(object):
    def __init__(self, stock, buying_delay):
        self.last_purchase = None
        self.stock = stock
        self.buying_delay = buying_delay

    def load_stock_data(self):
        today = datetime.date.today()
        try:
            df = pd.read_csv(
                f"price_data/{self.stock}.csv", index_col="Date")
            while today.weekday() > 4:
                today = today + datetime.timedelta(-1)
            if str(today) != df.iloc[-1].name:
                assert False
        except:
            df = pandas_datareader.data.DataReader(self.stock,
                                                   start='2020-5-1',
                                                   end=today.strftime(
                                                       "%m/%d/%Y"),
                                                   data_source='yahoo')
            df.to_csv(f"price_data/{self.stock}.csv")
        finally:
            return df

    def get_stock_quote(self, connection):
        api_key = os.environ['TRADIER_API_KEY']
        headers = {"Accept": "application/json",
                   "Authorization": api_key}
        connection.request(
            'GET', f'/v1/markets/quotes?symbols={self.stock}', None, headers)
        try:
            response = connection.getresponse()
            content = response.read().decode("utf-8")
            my_json = json.loads(content)
            return my_json
        except http.client.HTTPException as e:
            print("Exception during request", e)
            return None

    def market_is_open(self):
        tz = pytz.timezone('US/Eastern')
        us_holidays = holidays.US()
        now = datetime.datetime.now(tz)
        openTime = datetime.time(hour=9, minute=30, second=0)
        closeTime = datetime.time(hour=16, minute=0, second=0)
        abool = now.strftime('%Y-%m-%d') in us_holidays or now.time() < openTime or now.time() > closeTime \
            or now.date().weekday() > 4
        return not abool

    def buy_or_sell(self, df, portfolio, price, buying_condition):
        enough_time_passed = not self.last_purchase or datetime.date.today(
        ) - self.last_purchase > datetime.timedelta(self.buying_delay)
        if buying_condition.is_true(datetime.date.today(), price) and enough_time_passed:
            # buy; including add things to database
            pass
        # if selling_condition (i.e., plussed 60% of my position)

        # print('price', price)

    def run(self):
        connection = http.client.HTTPSConnection(
            'sandbox.tradier.com', 443, timeout=30)
        df = self.load_stock_data()
        portfolio = State.Portfolio()
        buying_condition = Conditions.IsLowForPeriod(
            df, portfolio, 3, week_length=7)
        while True:
            if self.market_is_open():
                my_json = self.get_stock_quote(connection)
                print(my_json)
                price = my_json['quotes']['quote']['last']
                self.buy_or_sell(df, portfolio, price, buying_condition)
            else:
                # reload the data
                df = self.load_stock_data()
                buying_condition = Conditions.IsLowForPeriod(
                    df, portfolio, 3, week_length=7)
                print("Market is closed")
            time.sleep(3)


if __name__ == "__main__":
    # logging.basicConfig(
    #     filename=f'logs/{datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")}.log',
    #     format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    #     datefmt='%Y-%m-%d:%H:%M:%S',
    #     level=logging.INFO)

    test = ForwardTesting("AMZN", buying_delay=5)
    test.run()
