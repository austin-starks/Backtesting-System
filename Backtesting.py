from datetime import date, timedelta
from pandas_datareader import data
import re
import pandas as pd
import math
import time
import logging
import Helper
import State
import os.path
import Conditions


def load_stock_data(stock):
    if os.path.exists(f"stock_price_data/daily/{stock}.csv"):
        df = pd.read_csv(
            f"stock_price_data/daily/{stock}.csv", index_col="Date")
    else:
        df = data.DataReader(stock,
                             start='1900-1-1',
                             end=date.today().strftime("%m/%d/%Y"),
                             data_source='yahoo')
        df.to_csv(f"stock_price_data/daily/{stock}.csv")
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
    date1 = [int(x) for x in re.split(r'[\-]', start_date)]
    date2 = [int(x) for x in re.split(r'[\-]', end_date)]
    date1_obj = date(date2[0], date2[1], date2[2])
    date2_obj = date(date1[0], date1[1], date1[2])
    epochs = (date1_obj - date2_obj).days
    date_is_valid = date_is_valid and epochs >= 0
    if not date_is_valid:
        Helper.log_error(f"start_date or end_date argument invalid. start_date: {start_date}; end_date: {end_date}\n" +
                         f"Expected a positive int or 'All' ")
    if not isinstance(resolution, State.Resolution):
        Helper.log_error(
            f"resolution argument invalid. resolution: {resolution}\nExpected enum of Resolution")
    if not (type(days) == int or days != "All" or days != 'all'):
        Helper.log_error(
            f"days argument invalid. days: {days}\nExpected a positive int or 'All'")
    Helper.log_info("Preconditions checked")


def backtest_helper(stock_list, current_date, state):
    Helper.log_info(stock_list, current_date)
    strategies = state.get_strategy_list()
    portfolio = state.get_portfolio()
    for strategy in strategies:
        stock = strategy.get_stock_name()
        buying_conditions = strategy.get_buying_conditions()
        for Condition in buying_conditions:
            condition = Condition(strategy.get_dataframe(),
                                  portfolio, current_date)
            if condition.is_true():
                print("Buy stock", stock)
        selling_conditions = strategy.get_selling_conditions()
        for condition in selling_conditions:
            if portfolio.contains(stock) and condition.is_true():
                print("Sell stock", stock)
    # print(portfolio.snapshot())


def backtest(stock_list, start_date, end_date, resolution, days):
    Helper.log_info("Starting Backtest")
    check_backtest_preconditions(start_date, end_date, resolution, days)
    if days == 'All' or days == 'all':
        date1 = [int(x) for x in re.split(r'[\-]', start_date)]
        date2 = [int(x) for x in re.split(r'[\-]', end_date)]
        date1_obj = date(date1[0], date1[1], date1[2])
        date2_obj = date(date2[0], date2[1], date2[2])
        epochs = (date2_obj - date1_obj).days
    elif type(days) == int and days > 0:
        epochs = days
    epochs, current_epoch = epochs * resolution, 0
    portfolio = State.Portfolio()
    strategy_list = []
    for stock in stock_list:
        df = load_stock_data(stock)
        # TODO: Implement conditions to buy/sell stock
        stock_strategy = State.StockStrategy(stock, df)
        stock_strategy.set_buying_conditions([Conditions.IsLowForWeek])
        stock_strategy.set_selling_conditions([])
        strategy_list.append(stock_strategy)

    state = State.BacktestingState(portfolio, strategy_list)
    while current_epoch <= epochs:
        try:
            if resolution == State.Resolution.DAYS:
                backtest_helper(stock_list, date1_obj +
                                timedelta(days=current_epoch), state)
            else:
                Helper.log_error(f"resolution {resolution} unimplemented")
        except KeyError:
            pass
        current_epoch += 1
    Helper.log_info("Backtest complete")


def main():
    logging.basicConfig(
        filename=f'logs/{math.ceil(time.time())}.log',
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.INFO)
    stock_list = ["AAPL", "SPY", "NVDA"]
    start_date, end_date = '2020-06-07', '2020-06-14'
    resolution = State.Resolution.DAYS
    backtest(stock_list, start_date, end_date, resolution, days='all')


if __name__ == "__main__":
    main()
