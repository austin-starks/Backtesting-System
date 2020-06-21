from datetime import date, datetime, timedelta
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
    if os.path.exists(f"price_data/daily/{stock}.csv"):
        df = pd.read_csv(
            f"price_data/daily/{stock}.csv", index_col="Date")
    else:
        df = data.DataReader(stock,
                             start='1900-1-1',
                             end=date.today().strftime("%m/%d/%Y"),
                             data_source='yahoo')
        df.to_csv(f"price_data/daily/{stock}.csv")
    return df


def load_crypto_data(crypto):
    df = pd.read_csv(
        f"price_data/hourly/{crypto}.csv", index_col="Date")
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


def backtest_buy(stock_name, stock_strategy, current_date, current_time, portfolio, stock_data):
    if stock_strategy.buying_conditions_are_met(current_date, current_time):
        buy_success = portfolio.buy(
            stock_name, stock_strategy, current_date, current_time)
        if buy_success:
            stock_strategy.ackowledge_buy(current_date, current_time)


def backtest_sell(stock_name, stock_strategy, current_date, current_time, portfolio, stock_data):
    if stock_strategy.must_be_profitable():
        is_profitable = portfolio.is_profitable(current_date, current_time)
    else:
        is_profitable = True
    if portfolio.contains(stock_name) and stock_strategy.selling_conditions_are_met(current_date, current_time, is_profitable):
        sell_success = portfolio.sell(
            stock_name, stock_strategy, current_date, current_time)
        if sell_success:
            stock_strategy.ackowledge_sell(current_date, current_time)


def backtest_loop_helper(asset_list, current_date, current_time, state):
    strategies = state.get_strategy_list()
    portfolio = state.get_portfolio()
    for stock_strategy in strategies:
        dataframe = stock_strategy.get_dataframe()
        stock_name = stock_strategy.get_asset_name()
        backtest_buy(stock_name, stock_strategy, current_date,
                     current_time, portfolio, dataframe)
        backtest_sell(stock_name, stock_strategy, current_date,
                      current_time, portfolio, dataframe)


def backtest_loop(asset_list, state, resolution, date1_obj, day_delta, current_time, current_epoch):
    if resolution == State.Resolution.Daily or resolution == State.Resolution.DAILY:
        try:
            current_date = date1_obj + timedelta(days=day_delta)
            # print("backtest_loop", current_date, current_time)

            backtest_loop_helper(
                asset_list, current_date, current_time, state)
        except KeyError:
            pass
    elif resolution == State.Resolution.Hourly or resolution == State.Resolution.HOURLY:
        current_date = date1_obj + timedelta(days=day_delta)
        # print("backtest_loop", current_date, current_time)
        backtest_loop_helper(
            asset_list, current_date, current_time, state)
    else:
        Helper.log_error(f"resolution {resolution} unimplemented")
    current_time.forward_time(resolution)


def backtest(asset_list, start_date, end_date, resolution, days, portfolio, strategy_list):
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
        day_delta = current_epoch // resolution
        backtest_loop(asset_list, state, resolution,
                      date1_obj, day_delta, current_time, current_epoch)
        current_epoch += 1
    Helper.log_info("Backtest complete")
    Helper.log_info(state.get_portfolio_snapshot(
        date1_obj + timedelta(days=day_delta), current_time))


def insert_strategy_list_stocks(asset_list, portfolio):
    strategy_list = []
    for stock in asset_list:
        df = load_stock_data(stock)
        stock_strategy = State.StockStrategy(
            stock, df, buying_allocation=0.30, selling_allocation=.10, buying_allocation_type='percent_bp')
        stock_strategy.set_buying_conditions(
            [Conditions.IsLowForPeriod(df, portfolio, 0)])
        stock_strategy.set_selling_conditions([
            Conditions.IsHighForPeriod(df, portfolio, 2)])
        strategy_list.append(stock_strategy)
    return strategy_list


def backtest_stocks(asset_list=["NVDA"], start_date='2020-01-01', end_date='2020-06-18'):
    portfolio = State.Portfolio()
    strategy_list = insert_strategy_list_stocks(asset_list, portfolio)
    resolution = State.Resolution.Daily
    backtest(asset_list, start_date, end_date,
             resolution, 'all', portfolio, strategy_list)


def insert_strategy_list_crypto(crypto_list, portfolio):
    strategy_list = []
    for crypto in crypto_list:
        df = load_crypto_data(crypto)
        stock_strategy = State.StockStrategy(
            crypto, df, buying_allocation=0.08, selling_allocation=.16,
            buying_allocation_type='percent_bp', must_be_profitable_to_sell=True, assets='crypto')
        stock_strategy.set_buying_conditions([
            Conditions.IsLowForPeriod(df, portfolio, -6, week_length=30)
        ])
        stock_strategy.set_selling_conditions([
            Conditions.IsHighForPeriod(df, portfolio, 6, week_length=30)
        ])
        strategy_list.append(stock_strategy)
    return strategy_list


def backtest_crypto(crypto_list=['BTC'], start_date='2018-05-10', end_date='2020-06-05'):
    portfolio = State.Portfolio(initial_cash=5000, trading_fees=2.00)
    strategy_list = insert_strategy_list_crypto(crypto_list, portfolio)
    resolution = State.Resolution.Hourly
    backtest(crypto_list, start_date, end_date,
             resolution, 'all', portfolio, strategy_list)


if __name__ == "__main__":
    logging.basicConfig(
        filename=f'logs/{datetime.now().strftime("%m-%d-%Y %H:%M:%S")}.log',
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.INFO)
    # backtest_stocks()
    backtest_crypto()
