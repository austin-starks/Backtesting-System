import datetime
import matplotlib.pyplot as plt
import re
import pandas as pd
import math
import time
import logging
import Helper
import State
import os
import os.path
import sys
import pytz
import holidays
import Conditions
from pathlib import Path


def market_is_open(now):
    us_holidays = holidays.US()
    abool = now.strftime('%Y-%m-%d') in us_holidays or now.weekday() > 4
    return not abool


def clear_logs():
    directory = 'logs'
    filelist = sorted([name for name in os.listdir(
        directory) if os.path.isfile(os.path.join(directory, name))])
    len_list = len(filelist)
    # print(filelist)
    i = 0
    for filename in filelist:
        # print(filename)
        os.remove(os.path.join(directory, filename))
        i += 1
        if i > len_list - 5:
            break


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
    date1_obj = datetime.date(date2[0], date2[1], date2[2])
    date2_obj = datetime.date(date1[0], date1[1], date1[2])
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


def backtest_buy(state, current_date, current_time, portfolio):
    if state.buying_conditions_are_met(current_date, current_time):
        stocks_to_buy = state.get_stocks_to_buy()
        abool = False
        # print(stocks_to_buy)
        for stock in stocks_to_buy:
            abool = abool or portfolio.buy(stock, state.get_strategies(),
                                           current_date, current_time)
            # print(abool)
        if abool:
            # print('bought')
            state.acknowledge_buy(current_date, current_time)


def backtest_sell(state, current_date, current_time, portfolio):
    stock_strategy = state.get_strategies()
    if stock_strategy.must_be_profitable():
        is_profitable = portfolio.is_profitable(current_date, current_time)
    else:
        is_profitable = True
    if is_profitable and state.selling_conditions_are_met(current_date, current_time, is_profitable):
        stocks_to_sell = state.get_stocks_to_sell()
        abool = False
        for stock in stocks_to_sell:
            abool = abool or portfolio.sell(stock, state.get_strategies(),
                                            current_date, current_time)
        if abool:
            state.acknowledge_sell(current_date, current_time)


def backtest_loop_helper(asset_list, current_date, current_time, state):
    portfolio = state.get_portfolio()
    backtest_buy(state, current_date, current_time, portfolio)
    backtest_sell(state, current_date, current_time, portfolio)


def backtest_loop(asset_list, state, resolution, date1_obj, epochs, current_time, current_epoch):
    while current_epoch <= epochs:
        day_delta = current_epoch // resolution
        current_date = date1_obj + datetime.timedelta(days=day_delta)
        # print("Backtest loop", current_date)
        if market_is_open(current_date):
            state.update_portfolio_value(current_date, current_time)
            backtest_loop_helper(asset_list, current_date, current_time, state)
        current_time.forward_time(resolution)
        current_epoch += 1
    return day_delta


def backtest(asset_list, start_date, end_date, resolution, days, state):
    Helper.log_info("Starting Backtest")
    check_backtest_preconditions(start_date, end_date, resolution, days)
    if days == 'All' or days == 'all':
        date1 = [int(x) for x in re.split(r'[\-]', start_date)]
        date2 = [int(x) for x in re.split(r'[\-]', end_date)]
        date1_obj = datetime.date(date1[0], date1[1], date1[2])
        date2_obj = datetime.date(date2[0], date2[1], date2[2])
        epochs = (date2_obj - date1_obj).days
    elif type(days) == int and days > 0:
        epochs = days
    epochs, current_epoch = epochs * resolution, 0
    current_time = State.Time(resolution)
    days_passed = backtest_loop(asset_list, state, resolution,
                                date1_obj, epochs, current_time, current_epoch)

    portfolio_history = state.get_portfolio_history()[0]
    portfolio_history.plot()
    plt.show()
    Helper.log_info("Backtest complete")
    Helper.log_info(state.get_portfolio_snapshot(
        date1_obj + datetime.timedelta(days=days_passed), current_time))


def construct_strategy(asset_list, portfolio, buying_allocation):
    strategy = State.HoldingsStrategy(
        "Buying monthlies at lows", asset_list, assets=State.Assets.Options, buying_allocation=buying_allocation, selling_allocation=1,
        maximum_allocation_per_stock=0.5, start_with_spreads=True, buying_delay=5, selling_delay=2, strikes_above=0,
        expiration_length=State.OptionLength.Monthly)
    strategy.set_buying_conditions(
        Conditions.IsLowForPeriod(portfolio, sd=0.5, week_length=5))
    strategy.set_selling_conditions(
        Conditions.NegaEndIsUpNPercent(portfolio, target_percent_gain=0.5))
    return strategy


def backtest_options(asset_list, start_date, end_date, strikes_above=0,
                     expiration_length=State.OptionLength.Monthly, buying_allocation=1):
    portfolio = State.Portfolio(initial_cash=10000, trading_fees=5.00)
    date1 = [int(x) for x in re.split(r'[\-]', start_date)]
    date1_obj = datetime.date(date1[0], date1[1], date1[2])
    strategy = construct_strategy(asset_list, portfolio, buying_allocation)

    state = State.BacktestingState(
        asset_list, portfolio, date1_obj, State.Resolution.Daily)
    state.add_strategy(strategy)
    resolution = State.Resolution.Daily
    backtest(asset_list, start_date, end_date,
             resolution, 'all', state)


if __name__ == "__main__":
    clear_logs()
    path = os.path.dirname(Path(__file__).absolute())

    logging.basicConfig(
        filename=f'{path}/logs/{datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")}.log',
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.INFO)

    # backtest_stocks()
    # backtest_crypto()
    backtest_options(asset_list=["NVDA"], expiration_length=State.OptionLength.Monthly,
                     start_date='2020-01-01', end_date='2020-07-24', strikes_above=1, buying_allocation=2)
    # backtest_options(asset_list=["NVDA"], expiration_length=State.OptionLength.Monthly,
    #                  start_date='2018-08-10', end_date='2019-07-24', strikes_above=1, buying_allocation=1)
