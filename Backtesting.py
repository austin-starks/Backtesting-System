import re 
import pandas as pd
from datetime import date, timedelta
import math
import time
import logging
import Helper
import State
import os.path
from pandas_datareader import data

def load_stock_data(stock):
    if os.path.exists(f"/stock_price_data/daily/{stock}.csv"):
        pass  
    else:
        df = data.DataReader(stock, 
                       start='2020-1-1', 
                       end=date.today().strftime("%m/%d/%Y"), 
                       data_source='yahoo')
        # df.to_csv(f"/stock_price_data/daily/{stock}.csv") 
        return df


def check_backtest_preconditions(start_date, end_date, resolution, days):
    Helper.log_info("Checking preconditions for backtest")
    start_arr = re.split(r'[\-]', start_date)
    end_arr = re.split(r'[\-]', end_date)
    date_is_valid = True
    for x, y in zip(start_arr, end_arr):
        date_is_valid = x.isdigit() and y.isdigit() and date_is_valid
        if date_is_valid:
            date_is_valid = date_is_valid and int(x) > 0 and int(y) > 0
    if not date_is_valid:
        Helper.log_error(f"start_date or end_date argument invalid. start_date: {start_date}; end_date: {end_date}\n"+
        f"Expected a positive int or 'All' ")
    if not isinstance(resolution, State.Resolution):
        Helper.log_error(f"resolution argument invalid. resolution: {resolution}\nExpected enum of Resolution")
    if not (type(days) == int or days != "All" or days != 'all'):
        Helper.log_error(f"days argument invalid. days: {days}\nExpected a positive int or 'All'")
    Helper.log_info("Preconditions checked")


def backtest_helper(stock_list, start_date, portfolio):
    Helper.log_info(stock_list, start_date)

def backtest(stock_list, start_date, end_date, resolution, days):
    Helper.log_info("Starting Backtest")
    check_backtest_preconditions(start_date, end_date, resolution, days)
    if days == 'All' or days == 'all':
        date1 = [int(x) for x in re.split(r'[\-]', start_date)]
        date2 = [int(x) for x in re.split(r'[\-]', end_date)]
        date1_obj = date(date2[0],date2[1],date2[2])
        date2_obj = date(date1[0],date1[1],date1[2])
        epochs = (date1_obj - date2_obj).days
    elif type(days) == int and days > 0:
        epochs = days  
    epochs = epochs * resolution
    print("epochs", epochs)
    portfolio = State.Portfolio()
    for epoch in range(epochs):
        if resolution == State.Resolution.DAYS:
            backtest_helper(stock_list, date1_obj + timedelta(days=epoch), portfolio)
        else: 
            Helper.log_error(f"resolution {resolution} unimplemented")
    Helper.log_info("Backtest complete")


if __name__ == "__main__":
    logging.basicConfig(
        filename=f'logs/{math.ceil(time.time())}.log', 
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.INFO)
    stock_list = ["AAPL"]
    stock_info_list = []
    for stock in stock_list:
        data = load_stock_data(data)
        print(data)
    # start_date, end_date = '2020-9-14', '2020-12-01'
    # resolution = State.Resolution.DAYS
    # # a map of stocks to the conditions in which you will buy/sell the stock
    # backtest(stock_list, start_date, end_date, resolution, days = 'all')