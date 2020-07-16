from datetime import date, datetime, timedelta
from pandas_datareader import data
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


def clear_logs():
    directory = 'logs'
    filelist = [name for name in os.listdir(
        directory) if os.path.isfile(os.path.join(directory, name))]
    len_list = len(filelist)
    if len_list > 10:
        for i in range(len_list - 5):
            filename = os.path.join(directory, filelist[i])
            os.remove(filename)


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


def backtest_buy(stock_strategy, current_date, current_time, portfolio, state):
    if stock_strategy.buying_conditions_are_met(current_date, current_time):
        buy_success = portfolio.buy(stock_strategy, current_date, current_time)
        if buy_success:
            state.acknowledge_buy(stock_strategy, current_date, current_time)


def backtest_sell(stock_strategy, current_date, current_time, portfolio, state):
    if stock_strategy.must_be_profitable():
        is_profitable = portfolio.is_profitable(current_date, current_time)
    else:
        is_profitable = True
    if is_profitable and stock_strategy.selling_conditions_are_met(current_date, current_time, is_profitable):
        sell_success = portfolio.sell(
            stock_strategy, current_date, current_time)
        if sell_success:
            state.acknowledge_sell(stock_strategy, current_date, current_time)


def backtest_loop_helper(asset_list, current_date, current_time, state):
    strategy = state.get_strategy()
    portfolio = state.get_portfolio()
    backtest_buy(strategy, current_date, current_time, portfolio, state)
    backtest_sell(strategy, current_date, current_time, portfolio, state)


def backtest_loop(asset_list, state, resolution, date1_obj, epochs, current_time, current_epoch):
    while current_epoch <= epochs:
        day_delta = current_epoch // resolution
        current_date = date1_obj + timedelta(days=day_delta)
        state.update_portfolio_value(current_date, current_time)
        backtest_loop_helper(asset_list, current_date, current_time, state)

        current_time.forward_time(resolution)
        current_epoch += 1
    return day_delta


def backtest(asset_list, start_date, end_date, resolution, days, state, plot_buy_sell_points=False):
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
    current_time = State.Time(resolution)
    days_passed = backtest_loop(asset_list, state, resolution,
                                date1_obj, epochs, current_time, current_epoch)

    portfolio_history, buy_history, sell_history = state.get_portfolio_history()
    ax = portfolio_history.plot()
    if plot_buy_sell_points:
        plt.rcParams.update({'font.size': 8})
        int_i = 0
        for buy in buy_history:
            x = (buy[0] - date1_obj).days * resolution
            y = 0.9 * state.get_portfolio().get_portfolio_value(
                date1_obj + timedelta(days=days_passed), current_time) - 500 * int_i
            y = 0.95**int_i * y
            plt.axvline(x=x, color='red', linestyle='dashed')
            ax.text(x=x, y=y, s=f'b {buy[1]}')
            int_i += 1
            if int_i >= 4:
                int_i = 0
        int_i = 0
        for sell in sell_history:
            x = (sell[0] - date1_obj).days * resolution
            y = 0.9 * state.get_portfolio().get_portfolio_value(
                date1_obj + timedelta(days=days_passed), current_time) - 500 * int_i
            y = 0.5**int_i * y
            plt.axvline(x=x, color='blue', linestyle='dashed')
            ax.text(x=x, y=y, s=f's {sell[1]}')
            int_i += 1
            if int_i >= 4:
                int_i = 0
    plt.show()
    Helper.log_info("Backtest complete")
    Helper.log_info(state.get_portfolio_snapshot(
        date1_obj + timedelta(days=days_passed), current_time))


def backtest_options(asset_list, start_date, end_date, include_buy_sells=True):
    portfolio = State.Portfolio(initial_cash=10000, trading_fees=5.00)
    date1 = [int(x) for x in re.split(r'[\-]', start_date)]
    date1_obj = date(date1[0], date1[1], date1[2])

    state = State.BacktestingState(
        portfolio, None, date1_obj, State.Resolution.Daily,
        allocation_hodl_dict_percent={'SPY': 1.0}, allocation_hodl_dict_data={'SPY': load_stock_data('SPY')}
    )
    resolution = State.Resolution.Daily
    backtest(asset_list, start_date, end_date,
             resolution, 'all', state, include_buy_sells)


if __name__ == "__main__":
    # clear_logs()
    base_dir = os.path.abspath('./logs')
    logging.basicConfig(
        filename=f'{base_dir}/{datetime.now().strftime("%m-%d-%Y %H:%M:%S")}.log',
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.INFO)
    # backtest_stocks()
    # backtest_crypto()
    backtest_options(asset_list=["CHGG"],
                     start_date='2020-02-14', end_date='2020-03-14', include_buy_sells=False)
    # backtest_options(asset_list=["QQQ"],
    #                  start_date='2020-06-01', end_date='2020-07-01', include_buy_sells=True)
    # backtest_options(asset_list=["NVDA", "SE", "DOCU", "AAPL", "SHOP", "TSLA"], start_date='2020-06-01', end_date='2020-07-01'):
