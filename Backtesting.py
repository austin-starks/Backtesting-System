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
import Conditions


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


def backtest_buy(stock_name, stock_strategy, current_date, current_time, portfolio, stock_data, state):
    if stock_strategy.buying_conditions_are_met(current_date, current_time):
        buy_success = portfolio.buy(
            stock_name, stock_strategy, current_date, current_time)
        if buy_success:
            state.acknowledge_buy(stock_strategy, current_date, current_time)


def backtest_sell(stock_name, stock_strategy, current_date, current_time, portfolio, stock_data, state):
    if stock_strategy.must_be_profitable():
        is_profitable = portfolio.is_profitable(current_date, current_time)
    else:
        is_profitable = True
    if portfolio.contains(stock_name) and stock_strategy.selling_conditions_are_met(current_date, current_time, is_profitable):
        sell_success = portfolio.sell(
            stock_name, stock_strategy, current_date, current_time)
        if sell_success:
            state.acknowledge_sell(stock_strategy, current_date, current_time)


def backtest_loop_helper(asset_list, current_date, current_time, state):
    strategies = state.get_strategy_list()
    portfolio = state.get_portfolio()
    for stock_strategy in strategies:
        dataframe = stock_strategy.get_dataframe()
        stock_name = stock_strategy.get_asset_name()
        backtest_buy(stock_name, stock_strategy, current_date,
                     current_time, portfolio, dataframe, state)
        backtest_sell(stock_name, stock_strategy, current_date,
                      current_time, portfolio, dataframe, state)


def backtest_loop(asset_list, state, resolution, date1_obj, day_delta, current_time, current_epoch):
    current_date = date1_obj + timedelta(days=day_delta)
    state.update_portfolio_value(
        current_date, current_time, state.get_strategy_list())
    backtest_loop_helper(
        asset_list, current_date, current_time, state)

    current_time.forward_time(resolution)


def backtest(asset_list, start_date, end_date, resolution, days, state, strategy_list, plot_buy_sell_points=False):
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
    while current_epoch <= epochs:
        day_delta = current_epoch // resolution
        backtest_loop(asset_list, state, resolution,
                      date1_obj, day_delta, current_time, current_epoch)
        current_epoch += 1
    portfolio_history, buy_history, sell_history = state.get_portfolio_history()
    ax = portfolio_history.plot()
    if plot_buy_sell_points:
        for buy in buy_history:
            x = (buy-date1_obj).days * resolution
            plt.axvline(x=x, color='red', linestyle='dashed')
            ax.text(x=x, y=13000, s='b')
        for sell in sell_history:
            x = (sell-date1_obj).days * resolution
            plt.axvline(x=x, color='blue', linestyle='dashed')
            ax.text(x=x, y=13000, s='s')
    plt.show()
    Helper.log_info("Backtest complete")
    Helper.log_info(state.get_portfolio_snapshot(
        date1_obj + timedelta(days=day_delta), current_time))


def insert_strategy_list_crypto(crypto_list, portfolio):
    strategy_list = []
    for crypto in crypto_list:
        df = load_crypto_data(crypto)
        stock_strategy = State.HoldingsStrategy(
            "Buy", crypto, df, buying_allocation=0.05, selling_allocation=0.05, minimum_allocation=0.4,
            buying_allocation_type='percent_bp', must_be_profitable_to_sell=True, assets='crypto',
            buying_delay=2)
        stock_strategy.set_buying_conditions([
            Conditions.IsLowForPeriod(df, portfolio, -1, week_length=10)
        ])
        stock_strategy.set_selling_conditions([
            Conditions.IsHighForPeriod(df, portfolio, 0, week_length=10)
        ])
        strategy_list.append(stock_strategy)

    return strategy_list


def backtest_crypto(crypto_list=['BTC'], start_date='2018-08-10', end_date='2019-03-10'):
    portfolio = State.Portfolio(initial_cash=4000, trading_fees=2.00)
    strategy_list = insert_strategy_list_crypto(crypto_list, portfolio)
    date1 = [int(x) for x in re.split(r'[\-]', start_date)]
    date1_obj = date(date1[0], date1[1], date1[2])
    # Fix HODL percent to be accurate
    state = State.BacktestingState(
        portfolio, strategy_list, date1_obj, State.Resolution.Hourly, allocation_hodl_dict_percent={
            'BTC': 1.0},
        allocation_hodl_dict_data={'BTC': load_crypto_data('BTC')})

    initial_holdings = []
    resolution = State.Resolution.Hourly
    initial_holdings.append(
        (crypto_list[0], 1000, "crypto", load_crypto_data(crypto_list[0])))
    # initial_holdings.append(
    #     (crypto_list[1], 800, "crypto", load_crypto_data(crypto_list[1])))
    state.add_initial_holdings(initial_holdings, start_date, resolution)
    backtest(crypto_list, start_date, end_date,
             resolution, 'all', state, strategy_list)


def insert_strategy_list_stocks(asset_list, portfolio):
    strategy_list = []
    for stock in asset_list:
        df = load_stock_data(stock)
        week_low = State.HoldingsStrategy(
            "Buy Boomers at week lows", stock, df, buying_allocation=0.05, buying_delay=3,
            selling_allocation=0.0, buying_allocation_type='percent_bp')
        week_low.set_buying_conditions(
            [Conditions.IsLowForPeriod(df, portfolio, 3, week_length=7)])
        week_low.set_selling_conditions(
            [Conditions.IsHighForPeriod(df, portfolio, 0, week_length=7)])
        strategy_list.append(week_low)

        # month_low = State.HoldingsStrategy(
        #     "Buy Boomers at month lows", stock, df, buying_allocation=0.25,
        #     selling_allocation=0.0, buying_allocation_type='percent_bp')
        # month_low.set_buying_conditions(
        #     [Conditions.IsLowForPeriod(df, portfolio, 0, week_length=30)])
        # strategy_list.append(month_low)
    return strategy_list


def backtest_stocks(asset_list=["NVDA"], start_date='2019-01-15', end_date='2019-06-15'):
    portfolio = State.Portfolio()
    date1 = [int(x) for x in re.split(r'[\-]', start_date)]
    date1_obj = date(date1[0], date1[1], date1[2])
    strategy_list = insert_strategy_list_stocks(asset_list, portfolio)
    state = State.BacktestingState(
        portfolio, strategy_list, date1_obj, State.Resolution.Daily)

    resolution = State.Resolution.Daily
    backtest(asset_list, start_date, end_date,
             resolution, 'all', state, strategy_list)


def insert_strategy_list_options(asset_list, portfolio):
    strategy_list = []
    for asset in asset_list:
        df = load_stock_data(asset)
        week_low = State.HoldingsStrategy(
            "Buy Boomers at week lows", asset, df, buying_allocation=1, buying_delay=7,
            selling_allocation=1, buying_allocation_type='percent_portfolio', assets='options',)
        week_low.set_buying_conditions(
            [Conditions.IsLowForPeriod(df, portfolio, 3, week_length=7)])
        strategy_list.append(week_low)
        nega_week_low = State.HoldingsStrategy(
            "Buy Nega-Boomers at week lows", asset, df, buying_allocation=-1, buying_delay=7,
            selling_allocation=1, buying_allocation_type='percent_portfolio', assets='options', strikes_above=1)
        nega_week_low.set_buying_conditions(
            [Conditions.IsLowForPeriod(df, portfolio, 3, week_length=7),
             Conditions.HasMoreBuyToOpen(df, portfolio, asset),
             ])
        strategy_list.append(nega_week_low)

        nega_week_low = State.HoldingsStrategy(
            "Sell Nega-Boomers when up n%", asset, df, buying_allocation=-1, buying_delay=7, selling_delay=4,
            selling_allocation=1, buying_allocation_type='percent_portfolio', assets='options', strikes_above=1)
        nega_week_low.set_selling_conditions(
            [Conditions.IsDownNPercent(df, portfolio, n=0.5),
             Conditions.IsSoldToOpen(df, portfolio),
             ])
        strategy_list.append(nega_week_low)

    return strategy_list


def backtest_options(asset_list, start_date, end_date, include_buy_sells=False):
    portfolio = State.Portfolio(initial_cash=6000, trading_fees=2.00)
    date1 = [int(x) for x in re.split(r'[\-]', start_date)]
    date1_obj = date(date1[0], date1[1], date1[2])
    strategy_list = insert_strategy_list_options(asset_list, portfolio)
    state = State.BacktestingState(
        portfolio, strategy_list, date1_obj, State.Resolution.Daily,
        # allocation_hodl_dict_percent={'QQQ': 1.0}, allocation_hodl_dict_data={'QQQ': load_stock_data('QQQ')}
    )
    resolution = State.Resolution.Daily
    backtest(asset_list, start_date, end_date,
             resolution, 'all', state, strategy_list, include_buy_sells)


if __name__ == "__main__":
    # clear_logs()
    logging.basicConfig(
        filename=f'logs/{datetime.now().strftime("%m-%d-%Y %H:%M:%S")}.log',
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.INFO)
    # backtest_stocks()
    # backtest_crypto()
    backtest_options(asset_list=["SE", "NVDA", "AAPL", "AMZN"],
                     start_date='2020-06-01', end_date='2020-07-01', include_buy_sells=True)
    # backtest_options(asset_list=["NVDA", "SE", "DOCU", "AAPL", "SHOP", "TSLA"], start_date='2020-06-01', end_date='2020-07-01'):
