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
    directory = os.path.dirname(Path(__file__).absolute()) + '/logs'
    filelist = sorted([name for name in os.listdir(
        directory) if os.path.isfile(os.path.join(directory, name))])
    len_list = len(filelist)
    # print(filelist)
    i = 0
    if len_list > 10:
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
    strategies = state.get_strategies()
    for strategy in strategies:
        if state.buying_conditions_are_met(strategy, current_date, current_time):
            stocks_to_buy = state.get_stocks_to_buy(strategy)
            abool = False
            # print(stocks_to_buy)
            for stock in stocks_to_buy:
                abool = abool or portfolio.buy(stock, strategy,
                                               current_date, current_time)
                # print(abool)
            if abool:
                # print('bought')
                state.acknowledge_buy(strategy, current_date, current_time)


def backtest_sell(state, current_date, current_time, portfolio):
    strategies = state.get_strategies()
    for strategy in strategies:
        if state.selling_conditions_are_met(strategy, current_date, current_time):
            stocks_to_sell = state.get_stocks_to_sell(strategy)
            abool = False
            for stock in stocks_to_sell:
                abool = abool or portfolio.sell(stock, strategy,
                                                current_date, current_time)
            if abool:
                state.acknowledge_sell(strategy, current_date, current_time)


def backtest_loop_helper(asset_list, current_date, current_time, state):
    portfolio = state.get_portfolio()
    backtest_buy(state, current_date, current_time, portfolio)
    backtest_sell(state, current_date, current_time, portfolio)


def backtest_loop(asset_list, state, resolution, date1_obj, epochs, current_time, current_epoch):
    while current_epoch <= epochs:
        day_delta = current_epoch // resolution
        current_date = date1_obj + datetime.timedelta(days=day_delta)
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


def sell_after_uncap_strategy(asset_list, portfolio, selling_allocation, selling_delay, target_percent_gain=0.5):
    strategy = State.HoldingsStrategy(
        "Selling option after uncapping for profit", asset_list, assets=State.Assets.Options, buying_allocation=0, selling_allocation=selling_allocation,
        maximum_allocation_per_stock=1.0, start_with_spreads=False, buying_delay=0, selling_delay=selling_delay, strikes_above=0)
    strategy.set_selling_conditions(
        Conditions.HasPosaEndThatsBooming(portfolio, target_percent_gain=target_percent_gain))

    return strategy


def sell_booming_nega_end(asset_list, portfolio, selling_allocation, selling_delay, target_percent_gain=0.5):
    strategy = State.HoldingsStrategy(
        "Selling booming nega-end for profit", asset_list, assets=State.Assets.Options, buying_allocation=0, selling_allocation=selling_allocation,
        maximum_allocation_per_stock=1.0, start_with_spreads=False, buying_delay=0, selling_delay=selling_delay, strikes_above=0)
    strategy.set_selling_conditions(
        Conditions.NegaEndIsUpNPercent(portfolio, target_percent_gain=0.5)
    )

    return strategy


def construct_long_strategy(asset_list, portfolio, buying_allocation, buying_delay, selling_delay,
                            option_type='C', spread_type='debit', strikes_above=0):
    strategy = State.HoldingsStrategy(
        "Going long at lows", asset_list, assets=State.Assets.Options, buying_allocation=buying_allocation, selling_allocation=1,
        maximum_allocation_per_stock=0.25, start_with_spreads=True, buying_delay=5, selling_delay=selling_delay, strikes_above=0,
        expiration_length=State.OptionLength.Monthly)
    strategy.set_buying_conditions(
        Conditions.IsLowForPeriod(portfolio, sd=0, week_length=5))
    return strategy


def construct_short_strategy(asset_list, portfolio, buying_allocation, buying_delay, selling_delay, spread_width=1,
                             option_type='P', spread_type='debit', strikes_above=0, expiration_length=State.OptionLength.Monthly):
    strategy = State.HoldingsStrategy(
        "Going short at highs", asset_list, assets=State.Assets.Options, buying_allocation=buying_allocation, selling_allocation=1,
        maximum_allocation_per_stock=0.15, start_with_spreads=True, buying_delay=buying_delay, selling_delay=selling_delay, strikes_above=strikes_above,
        expiration_length=State.OptionLength.Monthly, option_type=option_type, spread_type=spread_type, spread_width=spread_width)
    strategy.set_buying_conditions(
        Conditions.IsHighForPeriod(portfolio, sd=0, week_length=7))
    strategy.set_selling_conditions(
        Conditions.NegaEndIsUpNPercent(portfolio, target_percent_gain=0.5)
    )
    return strategy


def backtest_strategy(asset_list, start_date, end_date):
    portfolio = State.Portfolio(initial_cash=10000, trading_fees=5.00)
    date1 = [int(x) for x in re.split(r'[\-]', start_date)]
    date1_obj = datetime.date(date1[0], date1[1], date1[2])
    state = State.BacktestingState(
        asset_list, portfolio, date1_obj, State.Resolution.Daily)
    call_strategy = construct_long_strategy(
        asset_list, portfolio, buying_allocation=3, buying_delay=4, selling_delay=2, strikes_above=1)
    state.add_strategy(call_strategy)
    put_strategy = construct_short_strategy(
        asset_list, portfolio, buying_allocation=2, buying_delay=6, selling_delay=1, strikes_above=-1,
        expiration_length=State.OptionLength.TwoMonthly, spread_width=2)
    state.add_strategy(put_strategy)
    buy_nega_end_strategy = sell_booming_nega_end(
        asset_list, portfolio, selling_allocation=1, selling_delay=3, target_percent_gain=.5)
    state.add_strategy(buy_nega_end_strategy)
    # uncapped_sell_strategy = sell_after_uncap_strategy(
    #     asset_list, portfolio, selling_allocation=1, selling_delay=3, target_percent_gain=.5)
    # state.add_strategy(uncapped_sell_strategy)

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
    backtest_strategy(asset_list=["NVDA"],
                      start_date='2020-01-01', end_date='2020-07-01')

    # backtest_strategy(asset_list=["NVDA"],
    #                   start_date='2018-06-01', end_date='2019-01-20')
