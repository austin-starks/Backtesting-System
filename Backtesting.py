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


def backtest_helper(stock_list, current_date, current_time, state):
    strategies = state.get_strategy_list()
    portfolio = state.get_portfolio()
    for stock_strategy in strategies:
        dataframe = stock_strategy.get_dataframe()
        stock_name = stock_strategy.get_stock_name()
        if stock_strategy.buying_conditions_are_met(current_date, current_time):
            buy_success = portfolio.buy(
                stock_name, stock_strategy, current_date, current_time)
            if buy_success:
                today = dataframe.loc[str(current_date)]
                current_price = round(
                    today.loc[str(current_time)], 2)
                Helper.log_info(
                    f"Bought stock: {stock_name} on {current_date} at {current_time} for ${current_price}")
                stock_strategy.ackowledge_buy(current_date, current_time)
        if portfolio.contains(stock_name) and stock_strategy.selling_conditions_are_met(current_date, current_time):
            print("Sell stock", stock_name)


def backtest(stock_list, start_date, end_date, resolution, days, portfolio, strategy_list):
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
    state = State.BacktestingState(portfolio, strategy_list)
    current_time = State.Time(resolution)
    while current_epoch <= epochs:
        try:
            if resolution == State.Resolution.DAYS:
                day_delta = current_epoch / resolution
                backtest_helper(stock_list, date1_obj +
                                timedelta(days=day_delta), current_time, state)
            else:
                Helper.log_error(f"resolution {resolution} unimplemented")
            current_time.forward_time()
        except KeyError:
            pass
        current_epoch += 1
    Helper.log_info("Backtest complete")
    Helper.log_info(state.get_portfolio_snapshot())


def insert_strategy_list(stock_list, portfolio):
    strategy_list = []
    for stock in stock_list:
        df = load_stock_data(stock)
        stock_strategy = State.StockStrategy(stock, df)
        stock_strategy.set_buying_conditions(
            # make conditions more easily configurable
            [Conditions.IsLowForPeriod(df, portfolio, 0)])
        stock_strategy.set_selling_conditions([])
        strategy_list.append(stock_strategy)
    return strategy_list


def main():
    logging.basicConfig(
        filename=f'logs/{math.ceil(time.time())}.log',
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.INFO)
    stock_list = ["NVDA"]
    portfolio = State.Portfolio()
    strategy_list = insert_strategy_list(stock_list, portfolio)
    start_date, end_date = '2019-08-07', '2019-12-18'
    resolution = State.Resolution.DAYS
    backtest(stock_list, start_date, end_date,
             resolution, 'all', portfolio, strategy_list)


if __name__ == "__main__":
    main()
