from enum import IntFlag
import Conditions
from datetime import date, timedelta, datetime
import Helper
import pandas as pd
import requests
import os
import re


class BacktestingState(object):
    """
    A class that repreents all of the state during a backtest.

    This class holds information about the portfolio and current strategies for
    a backtest
    """

    def __init__(self, portfolio, strategy_list, current_date, resolution,
                 allocation_hodl_dict_percent=None, allocation_hodl_dict_data=None):
        if allocation_hodl_dict_data is not None:
            for data in allocation_hodl_dict_data:
                assert data in allocation_hodl_dict_percent
        if allocation_hodl_dict_percent is not None:
            for data in allocation_hodl_dict_percent:
                assert data in allocation_hodl_dict_data
        self._portfolio = portfolio
        self._strategy_list = strategy_list
        self._portfolio_history = pd.DataFrame(
            columns=["Strategy Value", "HODL Value"])
        self._history_length = 0
        current_time = str(Time(resolution))
        self._initial_datetime = current_date, current_time
        self._hodl_comparison_dict = dict()
        self._allocation_dict = allocation_hodl_dict_percent
        self._allocation_data = allocation_hodl_dict_data
        self.set_compare_function()

    def get_portfolio_history(self):
        """
        Returns: the portfolio history
        """
        return self._portfolio_history

    def set_compare_function(self):
        """
        Sets a hodl strategy to compare against a stock strategy/
        """
        current_date, current_time = self._initial_datetime
        if self._allocation_dict == None:
            self._allocation_data = dict()
            for strategy in self._strategy_list:
                name = strategy.get_asset_name()
                if name in self._hodl_comparison_dict:
                    continue
                price = strategy.get_stock_price(current_date, current_time)
                self._hodl_comparison_dict[name] = self._portfolio.get_initial_value(
                ) / price
                df = strategy.get_dataframe()
                self._allocation_data[name] = df
            len_holdings = len(self._hodl_comparison_dict)
            for holding in self._hodl_comparison_dict:
                self._hodl_comparison_dict[holding] = self._hodl_comparison_dict[holding]/len_holdings

        else:
            for key in self._allocation_data:
                df = self._allocation_data[key]
                price = HoldingsStrategy.get_stock_price_static(
                    df, current_date, current_time)
                self._hodl_comparison_dict[key] = (self._allocation_dict[key] * self._portfolio.get_initial_value(
                )) / price

    def get_strategy_list(self):
        """
        Returns: the strategy list for this stock in this state
        """
        return self._strategy_list

    def get_portfolio(self):
        """
        Returns: the portfolio in this state
        """
        return self._portfolio

    def get_portfolio_snapshot(self, date, time):
        """
        Returns: a snapshot of the portfolio
        """
        initial_value = self._portfolio_history.iloc[0]['Strategy Value']
        current_value = self._portfolio_history.iloc[-1]['Strategy Value']
        buying_power = self._portfolio.get_buying_power()
        holdings = self._portfolio.get_holdings()
        percent_change = round(100 * ((self._portfolio_history.iloc[-1] /
                                       self._portfolio_history.iloc[0]) - 1), 2)

        return f"Snapshot:\nInitial Value: {initial_value}\nCurrent Value: {current_value}" + \
            f"\nBuying Power: {buying_power}\nCurrent Holdings: {holdings}\n" + \
            f"Percent Change from Start: {percent_change['Strategy Value']}%\n" + \
            f"Percent Change for HODL: {percent_change['HODL Value']}%"

    def update_portfolio_value(self, cur_date, cur_time):
        """
        Adds the portfolio value (and HODL value)
        """
        strat_value = self._portfolio.get_portfolio_value(cur_date, cur_time)
        hodl_value = 0
        for key in self._hodl_comparison_dict:
            df = self._allocation_data[key]
            price = HoldingsStrategy.get_stock_price_static(
                df, cur_date, cur_time) * self._hodl_comparison_dict[key]
            hodl_value += price
            # print("allocation", self._hodl_comparison_dict[key])
            # print('price', price)

        self._portfolio_history.loc[self._history_length] = [
            strat_value, hodl_value]
        self._history_length += 1
        # print(self._portfolio_history)
        # update holdings
        # print("here")
        for holding in self._portfolio.get_holdings():
            # print('here2', holding.get_type())
            if holding.get_type() == 'options':
                expiration = holding.get_expiration()
                # print(expiration)
                expiration_match = re.match(
                    r"(\d{4})-(\d{2})-(\d{2})", expiration)
                expiration_obj = datetime(int(expiration_match.group(1)),
                                          int(expiration_match.group(2)), int(expiration_match.group(3)))
                # print(expiration.date() < date)
                # print(cur_date, expiration_obj.date())
                if cur_date > expiration_obj.date():
                    self._portfolio.liquidate(
                        holding, expiration_obj.date())

    def add_initial_holdings(self, holding_list, date, resolution):
        """
        Adds the initial holdings to the protfolio in this state
        """
        # print('before', self._hodl_comparison_dict)
        # print('price', price)
        # print(self._hodl_comparison_dict['BTC'] * price)
        initial_value = self._portfolio.get_initial_value()
        self._portfolio.add_initial_holdings(holding_list, date, resolution)
        final_value = self._portfolio.get_initial_value()
        percent_change = 1 + ((final_value - initial_value) / initial_value)
        # print("p change", percent_change)
        for holding_tup in holding_list:
            if holding_tup[0] in self._hodl_comparison_dict:
                self._hodl_comparison_dict[holding_tup[0]
                                           ] = self._hodl_comparison_dict[holding_tup[0]] * percent_change
        # print('after', self._hodl_comparison_dict)

    def calculate_HODL(self):
        return 0


class Holdings(object):
    """
    A class representing a holding

    This class contains information about currently held assets including the cost, the type
    of asset, and how much the person owns
    """

    def __init__(self, stock, num_assets, type_asset="stock"):
        self._asset_name = stock
        self._num_assets = num_assets
        self._type = type_asset
        if type_asset == 'options':
            match = re.match(r"\D+(\d{2})(\d{2})(\d{2})", stock)
            self._expiration = f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
        else:
            self._expiration = None

    def __hash__(self):
        return hash(self._asset_name + self._type)

    def __eq__(self, other):
        return self._asset_name == other._asset_name and self._type == other._type

    def __str__(self):
        return "(" + self._asset_name + " | Num assets: " + str(self._num_assets) + ")"

    def __repr__(self):
        return "(" + self._asset_name + " | Num assets: " + str(self._num_assets) + ")"

    def get_name(self):
        """
        Returns: the name of the holdings
        """
        return self._asset_name

    def get_expiration(self):
        """
        Returns: the expiration of this holding (for option holdings)
        """
        return self._expiration

    def get_type(self):
        """
        Returns: the type of holding
        """
        return self._type

    def get_num_assets(self):
        """
        Returns: the name of the holdings
        """
        return self._num_assets

    def add_shares(self, num_assets):
        """
        Adds additional shares to holdings
        """
        self._num_assets += num_assets

    def subtract_shares(self, num_assets):
        """
        Adds additional shares to holdings
        """
        self._num_assets -= num_assets


class HoldingsStrategy(object):
    """
    A class representing a trading strategy for a stock.

    This class holds information about a particular strategy for a stock. It
    includes the buying/selling conditions for the stock, and how many days
    between deploying the strategy can it be deployed again
    """

    def __init__(self, strategy_name, stock_name, data, buying_allocation=0.05, buying_allocation_type='percent_portfolio', maximum_allocation=1.0,
                 minimum_allocation=0.0, buying_delay=1, selling_allocation=0.1, assets='stocks', must_be_profitable_to_sell=False):
        self._strategy_name = strategy_name
        self._stock_name = stock_name
        self._buying_conditions = []
        self._selling_conditions = []
        self._buying_allocation_for_stock = buying_allocation
        self._buying_allocation_type = buying_allocation_type
        self._maximum_allocation_for_stock = maximum_allocation
        self._minimum_allocation_for_stock = minimum_allocation
        self._selling_allocation_for_stock = selling_allocation
        self._data = data
        self._delay = buying_delay
        self._last_purchase = None
        self._last_price = None
        self._last_sale = None
        self._assets = assets
        self._must_be_profitable = must_be_profitable_to_sell

    def __str__(self):
        """
        The string representation of this strategy
        """
        return f"Strategy {self._strategy_name} for {self._stock_name}"

    def __repr__(self):
        """
        The repr representation of this strategy
        """
        return f"Strategy {self._strategy_name} for {self._stock_name}"

    def must_be_profitable(self):
        """
        Returns: whether or not the portfolio must be profitable to sell.
        """
        return self._must_be_profitable

    def get_dataframe(self):
        """
        Returns: the dataframe for this stock strategy
        """
        return self._data

    def get_asset_name(self):
        """
        Returns: the buying conditions for this stock strategy
        """
        return self._stock_name

    def get_buying_conditions(self):
        """
        Returns: the buying conditions for this stock strategy
        """
        return self._buying_conditions

    def get_selling_conditions(self):
        """
        Returns: the selling conditions for this stock strategy
        """
        return self._selling_conditions

    def set_buying_conditions(self, condition_list):
        """
        Sets the buying condition to be condition_list
        """
        self._buying_conditions = condition_list

    def set_selling_conditions(self, condition_list):
        """
        Sets the selling condition to be condition_list
        """
        self._selling_conditions = condition_list

    def acknowledge_buy(self, date, time):
        """
        Sets last purchase to be a tuple of the last time this stock strategy bought an asset
        """
        self._last_purchase = (date, time)

    def acknowledge_sell(self, date, time):
        """
        Sets last sell to be a tuple of the last time this stock strategy sold an asset
        """
        self._last_sale = (date, time)

    def get_stock_price(self, date, time):
        """
        Returns: the current price of the stock at this date and time
        """
        if self._assets == 'stocks' or self._assets == 'options':
            i = 0
            while i < 3:
                try:
                    return round(self._data.loc[str(date - timedelta(i))].loc[str(time)], 2)
                except KeyError:
                    i = i + 1
        elif self._assets == 'crypto':
            return self._data.loc[f'{date} {time}'].loc['Open']

    def buying_conditions_are_met(self, date, time):
        """
        Returns: True if buying conditions are met; False otherwise
        """
        abool = False if self._buying_conditions == [] else True
        self._last_price = self.get_stock_price(date, time)
        for condition in self._buying_conditions:
            abool = abool and condition.is_true(date, time, self._assets)
        return abool and (self._last_purchase is None or self._last_purchase[0] + timedelta(self._delay) <= date)

    def selling_conditions_are_met(self, date, time, is_profitable=True):
        """
        Returns: True if selling conditions are met; False otherwise
        """
        abool = False if self._selling_conditions == [] else True
        for condition in self._selling_conditions:
            if self._must_be_profitable:
                abool = abool and condition.is_true(
                    date, time, self._assets) and is_profitable
            else:
                abool = abool and condition.is_true(date, time, self._assets)
        return abool and (self._last_sale is None or self._last_sale[0] + timedelta(self._delay) <= date)

    def get_buying_allocation(self):
        """
        Returns: The buying allocatin for this strategy
        """
        return self._buying_allocation_for_stock

    def get_buying_allocation_type(self):
        """
        Returns: The buying allocation for this strategy
        """
        return self._buying_allocation_type

    def get_maximum_allocation(self):
        """
        Returns: The maximum allocation for this strategy
        """
        return self._maximum_allocation_for_stock

    def get_minimum_allocation(self):
        """
        Returns: The minimum allocation for this strategy
        """
        return self._minimum_allocation_for_stock

    def get_selling_allocation(self):
        """
        Returns: The selling allocation for this strategy
        """
        return self._selling_allocation_for_stock

    def get_asset_type(self):
        """
        Returns: The asset type of this strategy
        """
        return self._assets

    @staticmethod
    def get_stock_price_static(df, date, time):
        """
        Returns: the current price of the stock at this date and time
        """
        # print("df")
        # print(df)
        if not 'Symbol' in df:
            i = 0
            while True:
                delta = timedelta(days=i)
                try:
                    # print(str(date + delta))
                    return round(df.loc[str(date + delta)].loc[str(time)], 2)
                except KeyError:
                    # print(df.iloc[-1].name)
                    expiration_match = re.match(
                        r"(\d{4})-(\d{2})-(\d{2})", df.iloc[-1].name)
                    expiration = datetime(int(expiration_match.group(1)),
                                          int(expiration_match.group(2)), int(expiration_match.group(3)))
                    # print(expiration.date() < date)
                    if expiration.date() < date:
                        return round(df.loc[str(expiration.date())].loc[str(time)], 2)
                    i -= 1
                    if i < -10:
                        raise KeyError
        else:
            return df.loc[str(date) + " " + str(time)].loc['Open']


class Portfolio(object):
    """
    A class representing a portfolio in a brokerage account.

    This class holds information to simulate a portfolio. It includes
    information like the starting amount, the current portfolio holdings,
    and trading fees
    """

    def __init__(self, initial_cash=100000.00,
                 current_holdings=[], past_holdings=[], trading_fees=0.75):

        self._current_holdings = current_holdings
        self._buying_power = initial_cash
        self._initial_value = initial_cash
        self._margin = 0  # will add margin later
        self._fees = trading_fees
        self._conditions = []
        self._strategies = dict()

    def liquidate(self, holding, expiration_date):
        """
        Sells all of this holding
        """
        abool = False
        holding_name = holding.get_name()
        df = self._strategies[holding_name]
        # print(df)
        # print(expiration_date)

        last_price = df.loc[str(expiration_date)].loc["Close"]
        # print(last_price)
        num_contracts = holding.get_num_assets()
        total_price = 100 * num_contracts * last_price

        abool = True
        self.increase_buying_power(total_price)
        self.subtract_holdings(holding_name, num_contracts, "options")
        Helper.log_info(
            f"{num_contracts} {holding_name} contracts expired on {expiration_date} for ${last_price} per share.")
        return abool

    def get_holdings(self):
        """
        Returns: the current holdings in this portfolio
        """
        return self._current_holdings

    def get_initial_value(self):
        """
        Returns: the intiial portfolio value
        """
        return self._initial_value

    def get_buying_power(self):
        """
        Returns: the current buying power of the portfolio
        """
        return self._buying_power

    def get_portfolio_value(self, date, time):
        """
        Returns: the value of all assets/cash in the portfolio
        """
        holdings_value = 0.0
        for holding in self._current_holdings:
            holdings_name = holding.get_name()
            # print(holdings_name[0])
            holdings_df = self._strategies[holdings_name]
            # print(holdings_df.head())
            # print("strategies", self._strategies)
            holdings_price = HoldingsStrategy.get_stock_price_static(
                holdings_df, date, time)
            if holding.get_type() == 'options':
                holdings_price = holdings_price * 100
            holdings_value += holding.get_num_assets() * holdings_price
        # print(date, time, holdings_value)
        # print(self._current_holdings)
        return self.get_buying_power() + holdings_value

    def is_profitable(self, date, time):
        """
        Returns: True if the portfolio is overall profitable. False otherwise.
        """
        return self.get_portfolio_value(date, time) > self._initial_value

    def contains(self, asset):
        """
        Returns: True if this portfolio contains stock. False otherwise.
        """
        for holding in self._current_holdings:
            if holding.get_name() == asset:
                return True
        return False

    def get_current_allocation(self, asset, last_price, date, time):
        """
        Returns: the total value asset in this portfolio.
        """
        if self.contains(asset):
            holdings_value = 0.0
            for holding in self._current_holdings:
                if holding.get_name() == asset:
                    holdings_value += holding.get_num_assets() * last_price
            return holdings_value
        else:
            return 0.0

    def get_current_allocation_percent(self, stock, last_price, date, time):
        """
        Returns: the percent of the portfolio that this stock makes up.
        """
        if self.contains(stock):
            holdings_value = 0.0
            for holding in self._current_holdings:
                if holding.get_name() == stock:
                    holdings_value += holding.get_num_assets() * last_price
            return holdings_value/self.get_portfolio_value(date, time)
        else:
            return 0.0

    def add_holdings(self, stock, num_shares, asset_type):
        """
        Adds the holdings to the portfolio
        """
        new_holding = Holdings(stock, num_shares, asset_type)
        if new_holding in self._current_holdings:
            ind = self._current_holdings.index(new_holding)
            holding = self._current_holdings[ind]
            holding.add_shares(num_shares)
        else:
            self._current_holdings.append(new_holding)

    def add_initial_holdings(self, holding_list, date, resolution):
        """
        Adds holding_list to the portfolio as an initial holding.

        Parameter holding_list: A 4-element tuple with the following format:
            (Name, Number Holdings, Asset type, Holdings data)
        """
        assert type(
            holding_list[0][0]) == str, 'Name of holding must be string'
        assert type(holding_list[0][1]) == float or type(
            holding_list[0][1]) == int, 'Number of holdings in the tuple must be number'
        assert type(holding_list[0][2]) == str, "Asset type must be a string"
        for holding_tup in holding_list:
            price = HoldingsStrategy.get_stock_price_static(
                holding_tup[3], date, str(Time(resolution)))
            if holding_tup[2] == 'crypto':
                num_shares = holding_tup[1] / price
            else:
                num_shares = int(holding_tup[1] // price)
            self.add_holdings(holding_tup[0], num_shares, holding_tup[2])
            self._initial_value += holding_tup[1]
            self.add_strategy_data_from_df(holding_tup[0], holding_tup[3])
            Helper.log_info(
                f"Added ${holding_tup[1]} of {holding_tup[0]} shares to the initial portfolio.")

    def subtract_holdings(self, stock, num_shares, asset_type):
        """
        Subtract the holdings to the portfolio
        """
        new_holding = Holdings(stock, num_shares, asset_type)
        if new_holding in self._current_holdings:
            ind = self._current_holdings.index(new_holding)
            holding = self._current_holdings[ind]
            holding.subtract_shares(num_shares)
            if holding.get_num_assets() == 0:
                del self._current_holdings[ind]
        else:
            Helper.log_error(
                "Selling shares you don't own. Exiting program...")

    def decrease_buying_power(self, cost):
        """
        Decreases the buying power by cost
        """
        self._buying_power = self._buying_power - (cost + self._fees)

    def increase_buying_power(self, gain):
        """
        Decreases the buying power by cost
        """
        self._buying_power = self._buying_power + (gain - self._fees)

    def add_strategy_data(self, strategy):
        """
        Adds the stock strategy to this portfolio
        """
        self._strategies[strategy.get_asset_name()] = strategy.get_dataframe()

    def add_strategy_data_from_df(self, name, df):
        """
        Adds the dataframe to the stock strategies list
        """
        self._strategies[name] = df

    def shares_to_buy(self, stock_strategy, buying_allocation, date, time, last_price):
        """
        Calculates the number of shares to buy
        """
        asset_type = stock_strategy.get_asset_type()
        type_allo = type(buying_allocation)
        buying_allo_type = stock_strategy.get_buying_allocation_type()
        if asset_type == 'stocks':
            if type_allo == int:
                dollars_to_spend = buying_allocation * last_price
                num_shares = buying_allocation
            elif type_allo == float:
                if buying_allo_type == 'percent_portfolio':
                    dollars_to_spend = self.get_portfolio_value(
                        date, time)*buying_allocation
                    num_shares = int(dollars_to_spend // last_price)
                elif buying_allo_type == 'percent_bp':
                    dollars_to_spend = self.get_buying_power()*buying_allocation
                    num_shares = int(dollars_to_spend // last_price)
                else:
                    Helper.log_error("Invalid buying allocation type")
            else:
                Helper.log_error(
                    f"Buying allocation should be an int or float")
            return num_shares, num_shares*last_price
        elif asset_type == 'crypto':
            if type_allo == int:
                dollars_to_spend = buying_allocation * last_price
                num_shares = buying_allocation
            elif type_allo == float:
                if buying_allo_type == 'percent_portfolio':
                    dollars_to_spend = self.get_portfolio_value(
                        date, time)*buying_allocation
                    num_shares = dollars_to_spend / last_price
                elif buying_allo_type == 'percent_bp':
                    dollars_to_spend = self.get_buying_power()*buying_allocation
                    num_shares = dollars_to_spend / last_price
                else:
                    Helper.log_error("Invalid buying allocation type")
            else:
                Helper.log_error(
                    f"Buying allocation should be an int or float")
            return num_shares, dollars_to_spend

    def get_options_data(self, stock, last_price, current_date, strikes_above=0, option_type='C'):
        """
        Returns: the dataframe representing the option that is 1 month from expiry from today 
        at a strike price just above strikes above.
        """
        strike = (last_price + 9 + strikes_above*10) // 10 * 10
        # Get strike price 4 weeks out
        friday = datetime(current_date.year,
                          current_date.month, current_date.day)
        friday = friday + timedelta(14)
        while friday.weekday() != 4:
            friday += timedelta(1)
        match = re.search(r"20(\d\d)-(\d\d)-(\d\d)", str(friday))
        str_price = str(int(strike))
        while len(str_price) < 5:
            str_price = '0' + str_price
        str_price = str_price + "000"
        symbol = f"{stock}{match.group(1)}{match.group(2)}{match.group(3)}{option_type}{str_price}"
        api_key = os.environ['TRADIER_API_KEY']
        try:
            # print('try', current_date)
            trade_data_response = requests.get('https://sandbox.tradier.com/v1/markets/history?',
                                               params={'symbol':  symbol,
                                                       'start': str(current_date)},
                                               headers={'Authorization': api_key,
                                                        'Accept': 'application/json'})
            trade_data_json = trade_data_response.json()
            # print('symbol', symbol)
            # print('json', trade_data_json)
            trade_data_arr = trade_data_json['history']['day']
            # print("current date", current_date)
            # print(trade_data_arr[0])
            dates = []
            trade_data = []
            for element in trade_data_arr:
                dates.append(element['date'])
                trade_data.append([element['open'], element['high'],
                                   element['low'], element['close'], element['volume']])
            df = pd.DataFrame(trade_data, index=dates,
                              columns=["Open", "High", "Low", "Close", "Volume"])
            # print(df.head())
            return df, symbol
        except:
            return None, ""

    def buy_options(self, stock, stock_strategy, cur_date, cur_time):
        """
        Helper function for buy to purchase options as opposed to shares.
        """
        # print("inside buy_options")
        abool = False
        last_price = stock_strategy.get_stock_price(cur_date, cur_time)
        # print(last_price)
        df, symbol = self.get_options_data(stock, last_price, cur_date)
        if df is None:
            # print("df is None")
            return abool
        else:
            # print('df.head')
            # print(df.head())
            pass
        num_contracts = stock_strategy.get_buying_allocation()
        # print('num contracts', num_contracts)
        # print(df)
        # print(df.loc[str(cur_date)][str(cur_time)])
        # print('before total')
        # print(df)
        # print(cur_date)

        # print(df.loc[str(cur_date)])
        try:
            total_price = 100*num_contracts * \
                df.loc[str(cur_date)][str(cur_time)]
            # print('after_total')
            # print('total_price', total_price)
            buying_power = self.get_buying_power()
            max_allocation = stock_strategy.get_maximum_allocation()
            # print('before if-statement')
            if self.get_current_allocation(stock, last_price, cur_date, cur_time) + total_price > \
                    max_allocation * self.get_portfolio_value(cur_date, cur_time):
                Helper.log_warn(
                    f"Portfolio currently has maximum allocation of {stock}")
            elif total_price < buying_power and total_price != 0.0:
                # print('total price', total_price)
                abool = True
                self.decrease_buying_power(total_price)
                self.add_holdings(symbol, num_contracts, 'options')
                self.add_strategy_data_from_df(symbol, df)
                Helper.log_info(
                    f"\nBought {num_contracts} {symbol} ({last_price}) contract(s) on {cur_date} at {cur_time} for ${df.loc[str(cur_date)][str(cur_time)]} per contract.\n{stock_strategy}\n---")
            else:
                Helper.log_warn(
                    f"\nInsufficent buying power to buy {stock}\n{stock_strategy}\n---")
            # print('after if-statement')
        except KeyError:
            pass
        finally:
            return abool

    def buy(self, stock, stock_strategy, date, time):
        """
        Buys stock according to the stock strategy. If buying allocation (in stock strategy)
        is an int, it will buy that many shares. Otherwise, it'll buy that percent of the
        portfolio worth of the stock.

        Returns: True if the buy is succcessful. False otherwise
        """
        abool = False
        asset_type = stock_strategy.get_asset_type()
        # print("inside buy", "asset_type", asset_type)
        if asset_type == 'options':
            answer = self.buy_options(stock, stock_strategy, date, time)
            # print("buy_options", answer)
            return answer
        buying_allocation = stock_strategy.get_buying_allocation()
        max_allocation = stock_strategy.get_maximum_allocation()
        last_price = stock_strategy.get_stock_price(date, time)
        num_shares, total_price = self.shares_to_buy(
            stock_strategy, buying_allocation, date, time, last_price)
        buying_power = self.get_buying_power()
        if self.get_current_allocation(stock, last_price, date, time) + total_price > \
                max_allocation * self.get_portfolio_value(date, time):
            Helper.log_warn(
                f"Portfolio currently has maximum allocation of {stock}")
        elif total_price < buying_power and total_price != 0.0:
            abool = True
            self.decrease_buying_power(total_price)
            self.add_holdings(stock, num_shares, asset_type)
            self.add_strategy_data(stock_strategy)
            Helper.log_info(
                f"\nBought {num_shares} {stock} shares on {date} at {time} for ${last_price} per share.\n{stock_strategy}\n---")
        else:
            Helper.log_warn(
                f"\nInsufficent buying power to buy {stock}\n{stock_strategy}\n---")
        return abool

    def sell(self, stock, stock_strategy, date, time):
        """
        Sells stock according to the stock_strategy
        """
        abool = False
        asset_type = stock_strategy.get_asset_type()
        last_price = stock_strategy.get_stock_price(date, time)
        current_value_holdings = self.get_current_allocation(
            stock, last_price, date, time)
        selling_allocation = stock_strategy.get_selling_allocation()
        if asset_type == 'stocks':
            estimated_shares_gain = selling_allocation * current_value_holdings
            shares_to_sell = int(estimated_shares_gain // last_price)
            exact_shares_gain = shares_to_sell * last_price
        elif asset_type == 'crypto':
            exact_shares_gain = selling_allocation * current_value_holdings
            shares_to_sell = exact_shares_gain / last_price
        min_allo = stock_strategy.get_minimum_allocation()
        portfolio_value = self.get_portfolio_value(date, time)
        current_allo = self.get_current_allocation(
            stock, last_price, date, time)
        if current_allo - exact_shares_gain < min_allo * portfolio_value:
            Helper.log_warn(
                f"Portfolio currently has minimum allocation of {stock}")
        else:
            abool = True
            self.increase_buying_power(exact_shares_gain)
            self.subtract_holdings(stock, shares_to_sell, asset_type)
            Helper.log_info(
                f"Sold {shares_to_sell} {stock} shares on {date} at {time} for ${last_price} per share.")
        return abool


class Resolution(IntFlag):
    """
    The resolution of data to backtest on.

    This Enum contains a list of data resolutions to analyze data from. The resolution can be in the magnitude of days
    (trading at open or at close), or can be in the timespan of minutes.
    """
    Daily = 2
    DAILY = 2
    Hourly = 24
    HOURLY = 24

    @staticmethod
    def time_init(resolution):
        if resolution == Resolution.Daily:
            return 'Open'
        assert False

    @staticmethod
    def forward_time(time, resolution):
        if resolution == Resolution.Daily:
            if time == 'Open':
                return 'Close'
            else:
                return "Open"
        Helper.log_error(f"Unimplemented resolution {resolution}")


class Time(object):
    """
    A class representing the current time
    """
    resolution_dict = {
        Resolution.Daily: ["Open", "Close"],
        Resolution.Hourly: ['12-AM', '01-AM', '02-AM', '03-AM', '04-AM', '05-AM', '06-AM', '07-AM', '08-AM', '09-AM',
                            '10-AM', '11-AM', '12-PM', '01-PM', '02-PM', '03-PM', '04-PM', '05-PM', '06-PM', '07-PM',
                            '08-PM', '09-PM', '10-PM', '11-PM']
    }

    def __init__(self, resolution):
        self._time = Time.resolution_dict[resolution]
        self._time_index = 0

    def forward_time(self, resolution):
        self._time_index += 1
        self._time_index %= resolution

    def __str__(self):
        return self._time[self._time_index]

    def __repr__(self):
        return self._time[self._time_index]

    def is_eod(self):
        return self._time_index == len(self._time) - 1
