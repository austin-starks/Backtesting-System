from enum import IntFlag, Enum
from datetime import date, timedelta, datetime
from pandas_datareader import data
import Helper
import pandas as pd
import requests
import os
import re
import calendar
from pathlib import Path
from collections import Counter


def load_stock_data(stock):
    # print('here')
    path = os.path.dirname(Path(__file__).absolute()) + '/price_data/daily'
    try:
        # print('here1', path)
        df = pd.read_csv(
            f"{path}/{stock}.csv", index_col="Date")
        the_date = date.today()
        while the_date.weekday() > 4:
            the_date -= timedelta(1)
        assert str(df.iloc[-1].name) == str(the_date)
    except:
        # print('here2', path)
        df = data.DataReader(stock,
                             start='2015-01-01',
                             end=date.today().strftime("%m/%d/%Y"),
                             data_source='yahoo')
        df.to_csv(f"{path}/{stock}.csv")
    return df


def load_crypto_data(crypto):
    df = pd.read_csv(
        f"price_data/hourly/{crypto}.csv", index_col="Date")
    return df


class Assets(Enum):
    Options = 'options'
    Stocks = 'stocks'
    Crypto = 'crypto'


class BacktestingState(object):
    """
    A class that repreents all of the state during a backtest.

    This class holds information about the portfolio and current strategies for
    a backtest
    """

    def __init__(self, portfolio, strategy, current_date, resolution):
        self._portfolio = portfolio
        self._strategy = strategy
        self._portfolio_history = pd.DataFrame(
            columns=["Strategy Value"])
        self._history_length = 0
        current_time = str(Time(resolution))
        self._initial_datetime = current_date, current_time
        self._buy_history = []
        self._sell_history = []
        self._last_purchase = None
        self._last_sale = None
        self._stocks_to_buy = set()
        self._stocks_to_sell = set()
        self._start_date = current_date

    def acknowledge_buy(self, date, time):
        """
        Sets last purchase to be a tuple of the last time this stock strategy bought an asset
        """
        self._last_purchase = (date, time)
        self._stocks_to_buy = set()
        self._stocks_to_sell = set()

    def acknowledge_sell(self, date, time):
        """
        Sets last sell to be a tuple of the last time this stock strategy sold an asset
        """
        self._last_sale = (date, time)
        self._stocks_to_sell = set()

    def get_stocks_to_buy(self):
        """
        Returns: the stocks that should be bought
        """
        return self._stocks_to_buy

    def get_start_date(self):
        """
        Returns: the start date of this state
        """
        return self._start_date

    def get_stocks_to_sell(self):
        """
        Returns: the stocks that should be sold
        """
        return self._stocks_to_sell

    def get_portfolio_history(self):
        """
        Returns: the portfolio history
        """
        return self._portfolio_history, self._buy_history, self._sell_history

    def get_strategy(self):
        """
        Returns: the stategy for this state
        """
        return self._strategy

    def buying_conditions_are_met(self, current_date, current_time):
        """
        Returns: True if buying conditions are met. False otherwise
        """
        if self._last_purchase and self._last_purchase[0] + timedelta(self._strategy.get_buying_delay()) > current_date:
            return False

        conditions_are_met = self._strategy.buying_conditions_are_met(
            current_date, current_time)

        if not conditions_are_met[0]:
            return False
        self._stocks_to_buy = set(conditions_are_met[1].keys())

        return True

    def selling_conditions_are_met(self, current_date, current_time, is_profitable=True):
        """
        Returns: True if selling conditions are met. False otherwise
        """
        if self._last_sale and self._last_sale[0] + timedelta(self._strategy.get_selling_delay()) > current_date:
            # print("Buying delay")
            return False

        conditions_are_met = self._strategy.selling_conditions_are_met(
            current_date, current_time, is_profitable)

        if not conditions_are_met[0]:
            return False
        self._stocks_to_sell = set(conditions_are_met[1].keys())
        return True

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
            f"Percent Change from Start: {percent_change['Strategy Value']}%"
        # f"Percent Change for HODL: {percent_change['HODL Value']}%"

    def update_portfolio_value(self, cur_date, cur_time):
        """
        Adds the portfolio value (and HODL value)
        """
        # print("here....!")

        strat_value = self._portfolio.get_portfolio_value(cur_date, cur_time)
        # hodl_value = 0
        # for key in self._hodl_comparison_dict:
        #     price = self._strategy.get_stock_price(
        #         key, cur_date, cur_time) * self._hodl_comparison_dict[key]
        #     hodl_value += price

        self._portfolio_history.loc[self._history_length] = strat_value
        self._history_length += 1
        # update holdings
        holdings = self._portfolio.get_holdings()
        # print(holdings)
        positions_to_sell = {}
        for key in holdings:
            holding = holdings[key]
            if holding.get_type() == Assets.Options:
                positions = holding.get_positions()
                for position in positions:
                    # print("position", position)

                    expiration_match = re.match(
                        r"(\D+)(\d{2})(\d{2})(\d{2})", str(position))
                    # print(expiration_match)
                    expiration_obj = datetime(int('20' + expiration_match.group(2)),
                                              int(expiration_match.group(3)), int(expiration_match.group(4)))

                    if cur_date > expiration_obj.date():
                        num_positions = positions[position][0]
                        positions_to_sell[position] = num_positions
        for position in positions_to_sell:
            self._portfolio.liquidate(
                key, position, expiration_obj.date(), num_positions)

    def add_initial_holdings(self, holding_list, date, resolution):
        """
        Adds the initial holdings to the protfolio in this state
        """
        # initial_value = self._portfolio.get_initial_value()
        self._portfolio.add_initial_holdings(holding_list, date, resolution)
        # final_value = self._portfolio.get_initial_value()
        # percent_change = 1 + ((final_value - initial_value) / initial_value)
        # for holding_tup in holding_list:
        #     if holding_tup[0] in self._hodl_comparison_dict:
        #         self._hodl_comparison_dict[holding_tup[0]
        #                                    ] = self._hodl_comparison_dict[holding_tup[0]] * percent_change

    def calculate_HODL(self):
        return 0


class Holdings(object):
    """
    A class representing a holding

    This class contains information about currently held assets including the cost, the type
    of asset, and how much the person owns
    """
    options_prices = {}
    failed_options_prices = {}

    def __init__(self, holding_name, num_shares, initial_price, options_df=None, type_asset=Assets.Stocks,
                 initial_purchase_date=None):
        self._type = type_asset
        # print(holding_name, type(holding_name))
        if Helper.hasNumbers(holding_name):
            match = re.match(r"(\D+)(\d{2})(\d{2})(\d{2})", holding_name)
            self._underlying_name = match.group(1)
            # self._expiration = f"20{match.group(2)}-{match.group(3)}-{match.group(4)}"
        else:
            self._underlying_name = holding_name
            # self._expiration = None
        self._position_list = dict()
        self._position_list[holding_name] = [num_shares, initial_price]
        self._initial_purchase_date = initial_purchase_date
        # print(holding_name, num_shares, options_df, type_asset)
        # print("options df init", options_df)
        Holdings.options_prices[holding_name] = options_df

    def __hash__(self):
        return hash(self._underlying_name)

    def __eq__(self, other):
        return self._underlying_name == other._underlying_name

    def __str__(self):
        return f"({self._underlying_name} | Positions: {str(self.get_positions())} | Initial Purchase: {str(self._initial_purchase_date)})"

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def get_options_symbol(stock, last_price, current_date, strikes_above=0, option_type='C'):
        strikes_above = strikes_above * -1 if option_type == 'P' else strikes_above
        if last_price < 20:
            strike = round(last_price + strikes_above)
        elif last_price < 100:
            strike = 5 * round((last_price + 5 * strikes_above) / 5)
        else:
            strike = 10 * round((last_price + 10 * strikes_above) / 10)
        # Get strike price 4 weeks out
        friday = Portfolio._option_expiration(current_date)
        if friday.date() - current_date < timedelta(14):
            friday = Portfolio._option_expiration(friday + timedelta(28))
        match = re.search(r"20(\d\d)-(\d\d)-(\d\d)", str(friday))
        str_price = str(int(strike))
        while len(str_price) < 5:
            str_price = '0' + str_price
        str_price = str_price + "000"
        symbol = f"{stock}{match.group(1)}{match.group(2)}{match.group(3)}{option_type}{str_price}"
        return symbol

    @staticmethod
    def get_options_data(symbol):
        """
        Returns: the dataframe representing the option that is 1 month from expiry from today
        at a strike price just above strikes above.
        """
        # print(symbol, Holdings.options_prices.keys())
        if symbol in Holdings.failed_options_prices:
            return None
        if symbol in Holdings.options_prices and Holdings.options_prices[symbol] is not None:
            # print('shortcut', symbol)
            # print("price df", Holdings.options_prices)
            # print(f"LOCAL MEMORY FOR {symbol}")
            return Holdings.options_prices[symbol]
        else:
            api_key = os.environ['TRADIER_API_KEY']
            # print(f"API REQUEST FOR {symbol}")
            try:
                # print("Doing API request...")
                trade_data_response = requests.get('https://sandbox.tradier.com/v1/markets/history?',
                                                   params={'symbol': symbol,
                                                           'start': '2015-01-01'},
                                                   headers={'Authorization': api_key,
                                                            'Accept': 'application/json'})
                # print("Response:", trade_data_response)
                trade_data_json = trade_data_response.json()
                # print("JSON:", trade_data_json)
                trade_data_arr = trade_data_json['history']['day']
                dates = []
                trade_data = []
                for element in trade_data_arr:
                    dates.append(element['date'])
                    trade_data.append([element['open'], element['high'],
                                       element['low'], element['close'], element['volume']])
                df = pd.DataFrame(trade_data, index=dates,
                                  columns=["Open", "High", "Low", "Close", "Volume"])
                # print(df)
                Holdings.options_prices[symbol] = df
                # print(Holdings.options_prices)
                return df
            except Exception as e:
                Helper.log_warn(f"Exception: {e}")
                Holdings.failed_options_prices[symbol] = True
                # Helper.log_warn(trade_data_response)
                # Helper.log_warn(trade_data_json)
                return None

    @staticmethod
    def get_options_price(options_name, current_date, time):
        """
        Returns: the current price of the stock at this date and time
        """
        df = Holdings.get_options_data(options_name)
        i = 0
        while True:
            delta = timedelta(days=i)
            try:
                # print("date", current_date)
                # print("date and delta", str(current_date + delta))
                return round(df.loc[str(current_date + delta)].loc[str(time)], 2)
            except KeyError:
                # print(str(df.iloc[-1].name))
                expiration_match = re.match(
                    r"(\d{4})-(\d{2})-(\d{2})", str(df.iloc[-1].name))
                expiration = datetime(int(expiration_match.group(1)),
                                      int(expiration_match.group(2)), int(expiration_match.group(3)))
                # print(df.tail())
                # print(date)
                # print(time)
                if expiration.date() < current_date:
                    return round(df.loc[str(expiration.date())].loc[str(time)], 2)
                i -= 1
                if i < -5:
                    j = 0
                    iloc = df.iloc[j]
                    date_arr = [int(x)
                                for x in re.split(r'[\-]', iloc.name)]
                    date_obj = date(date_arr[0], date_arr[1], date_arr[2])

                    while current_date > date_obj:
                        j += 1
                        iloc = df.iloc[j]
                        date_arr = [int(x)
                                    for x in re.split(r'[\-]', iloc.name)]
                        date_obj = date(
                            date_arr[0], date_arr[1], date_arr[2])
                    iloc2 = df.iloc[j - 1]
                    date_arr2 = [int(x)
                                 for x in re.split(r'[\-]', iloc2.name)]
                    date_obj2 = date(
                        date_arr2[0], date_arr2[1], date_arr2[2])
                    # print("date obj", date_obj)
                    # print("date obj2", date_obj2)
                    if j == 0:
                        answer = (df.loc[str(date_obj)].loc[str(time)])
                    else:
                        answer = (df.loc[str(date_obj)].loc[str(
                            time)] + df.loc[str(date_obj2)].loc[str(time)]) / 2
                    answer = round(answer, 2)
                    Helper.log_warn(
                        f"Options price not found; estimating options price for {options_name} at ${answer} on {current_date}")
                    # Helper.log_warn(df)
                    Helper.log_warn(f"Date not found: {current_date}")
                    return answer

    def get_underlying_name(self):
        """
        Returns: the underlying name of the holdings
        """
        return self._underlying_name

    def get_type(self):
        """
        Returns: the type of holding
        """
        return self._type

    def is_empty(self):
        """
        Returns: True if there is no holding in this holdings object. False otherwise
        """
        return self._position_list == dict()

    def get_positions(self):
        """
        Returns: the positions in this holding.
        """
        return self._position_list

    def add_shares(self, stock_name, num_assets, dataframe, price):
        """
        Adds additional shares to holdings
        """
        # include price
        # print(self._position_list)
        if stock_name in self._position_list:
            # print('if')
            position_info = self._position_list[stock_name]
            positions_before_adding = position_info[0]
            # print("position info", position_info)
            position_info[0] += num_assets
            if position_info[0] != 0:
                position_info[1] = (position_info[1] + price *
                                    num_assets) / (positions_before_adding + num_assets)

            Holdings.options_prices[stock_name] = dataframe
        else:
            # print('else1')
            self._position_list[stock_name] = [num_assets, price]
            # print("else", self._position_list, [num_assets, price])
        if self._position_list[stock_name][0] == 0:
            del self._position_list[stock_name]

    def subtract_shares(self, stock_name, num_assets):
        """
        Adds additional shares to holdings
        """
        self._position_list[stock_name][0] -= num_assets
        if self._position_list[stock_name][0] == 0:
            del self._position_list[stock_name]


class HoldingsStrategy(object):
    """
    A class representing a trading strategy for a stock.

    This class holds information about a particular strategy for a stock. It
    includes the buying/selling conditions for the stock, and how many days
    between deploying the strategy can it be deployed again
    """

    def __init__(self, strategy_name, asset_list, buying_allocation=1, buying_allocation_type='percent_portfolio', maximum_allocation_per_stock=100000000, option_type='C',
                 minimum_allocation=0.0, buying_delay=1, selling_delay=0, selling_allocation=0.1, assets=Assets.Stocks, must_be_profitable_to_sell=False,
                 strikes_above=0, start_with_spreads=True):
        self._strategy_name = strategy_name
        self._asset_info = dict()
        self._stock_list = asset_list
        self._assets = assets
        for stock in asset_list:
            if assets != 'crypto':
                self._asset_info[stock] = load_stock_data(stock)
            else:
                self._asset_info[stock] = load_crypto_data(stock)
        self._buying_conditions = []
        self._selling_conditions = []
        self._stocks_to_buy = []
        self._stocks_to_sell = []
        self._buying_allocation_for_stock = buying_allocation
        self._buying_allocation_type = buying_allocation_type
        self._maximum_allocation_for_stock = maximum_allocation_per_stock
        self._minimum_allocation_for_stock = minimum_allocation
        self._selling_allocation_for_stock = selling_allocation
        self._buying_delay = buying_delay
        self._selling_delay = selling_delay
        self._last_price = None
        self._must_be_profitable = must_be_profitable_to_sell
        self._strikes_above = strikes_above
        self._option_type = option_type
        self._start_with_spreads = start_with_spreads

    def __str__(self):
        """
        The string representation of this strategy
        """
        return f"Strategy {self._strategy_name} for {self._stock_list}"

    def __repr__(self):
        """
        The repr representation of this strategy
        """
        return f"Strategy {self._strategy_name} for {self._stock_list}"

    def must_be_profitable(self):
        """
        Returns: whether or not the portfolio must be profitable to sell.
        """
        return self._must_be_profitable

    def get_asset_names(self):
        """
        Returns: the asset names
        """
        return self._stock_list

    def get_buying_delay(self):
        """
        Returns: the buying delay
        """
        return self._buying_delay

    def get_selling_delay(self):
        """
        Returns: the buying delay
        """
        return self._selling_delay

    def start_with_spreads(self):
        """
        Returns: True if the options strategy starts with buying a spread. False otherwise.
        """
        return self._start_with_spreads

    def get_asset_info(self):
        """
        Returns: The dataframes for stocks in this stock strategy
        """
        return self._asset_info

    def get_option_type(self):
        """
        Returns: the option type
        """
        return self._option_type

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

    def set_buying_conditions(self, buying_conditions):
        """
        Sets the buying conditions to buying_conditon
        """
        self._buying_conditions = buying_conditions

    def set_selling_conditions(self, selling_conditions):
        """
        Sets the selling conditions to selling_conditon
        """
        self._selling_conditions = selling_conditions

    def get_strikes_above(self):
        """
        Returns: the stock strategy's strikes above if this strategy is an option
        """
        return self._strikes_above

    def get_stock_price(self, stock, current_date, time):
        """
        Returns: the current price of the stock at this date and time
        """
        df = self._asset_info[stock]
        return round(df.loc[str(current_date)].loc[str(time)], 2)

    @staticmethod
    def get_stock_price_static(stock, current_date, time):
        """
        Returns: the current price of the stock at this date and time
        """
        df = load_stock_data(stock)
        return round(df.loc[str(current_date)].loc[str(time)], 2)

    def buying_conditions_are_met(self, date, time):
        """
        Returns: True if buying conditions are met; False otherwise
        """
        return self._buying_conditions.is_true(date, time)

    def selling_conditions_are_met(self, date, time, is_profitable=True):
        """
        Returns: True if selling conditions are met; False otherwise
        """
        return self._selling_conditions.is_true(date, time)

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


class Portfolio(object):
    """
    A class representing a portfolio in a brokerage account.

    This class holds information to simulate a portfolio. It includes
    information like the starting amount, the current portfolio holdings,
    and trading fees
    """

    def __init__(self, initial_cash=100000.00,
                 trading_fees=0.75):

        self._current_holdings = {}
        self._buying_power = initial_cash
        self._initial_value = initial_cash
        self._margin = 0  # will add margin later
        self._fees = trading_fees
        self._conditions = []

    def liquidate(self, stock_name, option_name, expiration_date, num_contracts):
        """
        Sells all of this holding
        """
        abool = False
        # change last price to get last options price at this date
        last_price = Holdings.get_options_price(
            option_name, expiration_date, "Close")
        total_price = 100 * num_contracts * last_price
        abool = True
        if last_price == 0.01:
            total_price = 0
        self.increase_buying_power(total_price)
        self.subtract_holdings(option_name, num_contracts)
        Helper.log_info(
            f"\n{abs(num_contracts)} {option_name} contracts expired on {expiration_date} for ${last_price} per share.\n---")
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
        for holding_name in self._current_holdings:
            holding = self._current_holdings[holding_name]
            if holding.get_type() == Assets.Options:
                positions = holding.get_positions()
                for position in positions:
                    price = Holdings.get_options_price(
                        position, date, time) * 100
                    num_assets = positions[position][0]
                    holdings_value += num_assets * price
            else:
                Helper.log_error("Unimplemented")
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
            if holding.get_underlying_name() == asset:
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
            return holdings_value / self.get_portfolio_value(date, time)
        else:
            return 0.0

    def add_holdings(self, stock, num_shares, price, asset_type, initial_purchase_date, options_dateframe=None):
        """
        Adds the holdings to the portfolio
        """
        new_holding = Holdings(stock, num_shares, price, options_dateframe,
                               asset_type, initial_purchase_date)
        name = new_holding.get_underlying_name()
        if name in self._current_holdings:
            holding = self._current_holdings[name]
            holding.add_shares(stock, num_shares, options_dateframe, price)
            if holding.is_empty():
                del self._current_holdings[name]
        else:
            self._current_holdings[name] = new_holding

    def subtract_holdings(self, stock, num_shares):
        """
        Subtract the holdings to the portfolio
        """
        new_holding = Holdings(stock, num_shares, 0, None)
        name = new_holding.get_underlying_name()
        if name in self._current_holdings:
            holding = self._current_holdings[name]
            holding.subtract_shares(stock, num_shares)
            if holding.is_empty():
                del self._current_holdings[name]
        else:
            Helper.log_error(
                f"Selling shares you don't own: {stock}. Exiting program...")

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
                        date, time) * buying_allocation
                    num_shares = int(dollars_to_spend // last_price)
                elif buying_allo_type == 'percent_bp':
                    dollars_to_spend = self.get_buying_power() * buying_allocation
                    num_shares = int(dollars_to_spend // last_price)
                else:
                    Helper.log_error("Invalid buying allocation type")
            else:
                Helper.log_error(
                    f"Buying allocation should be an int or float")
            return num_shares, num_shares * last_price
        elif asset_type == 'crypto':
            if type_allo == int:
                dollars_to_spend = buying_allocation * last_price
                num_shares = buying_allocation
            elif type_allo == float:
                if buying_allo_type == 'percent_portfolio':
                    dollars_to_spend = self.get_portfolio_value(
                        date, time) * buying_allocation
                    num_shares = dollars_to_spend / last_price
                elif buying_allo_type == 'percent_bp':
                    dollars_to_spend = self.get_buying_power() * buying_allocation
                    num_shares = dollars_to_spend / last_price
                else:
                    Helper.log_error("Invalid buying allocation type")
            else:
                Helper.log_error(
                    f"Buying allocation should be an int or float")
            return num_shares, dollars_to_spend

    @staticmethod
    def _option_expiration(date):
        now = date
        first_day_of_month = datetime(now.year, now.month, 1)
        first_friday = first_day_of_month + \
            timedelta(
                days=((4 - calendar.monthrange(now.year, now.month)[0]) + 7) % 7)
        # 4 is friday of week
        return first_friday + timedelta(days=14)

    def check_max_allocation(self, stock_name, stock_strategy, cur_date, cur_time):
        """
        Returns True if the stock is below its maximum allocation allowed. False otherwise
        """
        max_allocation = stock_strategy.get_maximum_allocation()
        if type(max_allocation) == int:
            max_allocation = max_allocation
        else:
            max_allocation = max_allocation * \
                self.get_portfolio_value(cur_date, cur_time)
        # check max allocation
        tmp_holding = Holdings(stock_name, 0, 0)
        name = tmp_holding.get_underlying_name()
        # print("name", name)
        # print("self._current_holdings:", self._current_holdings)
        # print("name in self._current_holdings", name in self._current_holdings)
        count = 0
        if name in self._current_holdings:
            # print('here2')
            positions = self._current_holdings[name].get_positions()
            for position in positions:
                count += Holdings.get_options_price(
                    position, cur_date, cur_time) * positions[position][0]
        # print(stock_name, cur_date, count, max_allocation)
        return count * 100 < max_allocation
        # print('here1')

    def buy_options(self, stock, stock_strategy, cur_date, cur_time):
        """
        Helper function for buy to purchase options as opposed to shares.
        """
        abool = False
        last_price = stock_strategy.get_stock_price(stock, cur_date, cur_time)
        symbol = Holdings.get_options_symbol(
            stock, last_price, cur_date, stock_strategy.get_strikes_above(), stock_strategy.get_option_type())
        if not self.check_max_allocation(symbol, stock_strategy, cur_date, cur_time):
            Helper.log_warn(
                f"Portfolio currently has maximum allocation of {stock}")
            return abool
        # TODO Also, make all data saved to local database and attempt to fetch from there
        df = Holdings.get_options_data(symbol)
        if df is None:
            return abool
        num_contracts = stock_strategy.get_buying_allocation()
        holdings_price = Holdings.get_options_price(symbol, cur_date, cur_time)
        total_price = 100 * num_contracts * holdings_price
        buying_power = self.get_buying_power()
        if total_price < buying_power and total_price != 0.0:
            # print('here3')
            abool = True
            self.decrease_buying_power(total_price)
            self.add_holdings(symbol, num_contracts, holdings_price,
                              Assets.Options, cur_date, df)
            # print('here4')
            if total_price > 0:
                Helper.log_info(
                    f"\nBought (to open) {num_contracts} {symbol} (${holdings_price} stock price) contract(s) on {cur_date} at {cur_time} for " +
                    f"${holdings_price} per contract.\n{stock_strategy}\n---")
            else:
                Helper.log_info(
                    f"\nSold (to open) {-1 * num_contracts} {symbol} (${holdings_price} stock price) contract(s) on " +
                    f"{cur_date} at {cur_time} for ${holdings_price} per contract.\n{stock_strategy}\n---")
        else:
            abool = False
            Helper.log_warn(
                f"Insufficent buying power to buy {stock} on {cur_date} at {cur_time}\n{stock_strategy}\n---")
        return abool

    def buy_spreads(self, stock, stock_strategy, cur_date, cur_time):
        """
        Helper function for buy to purchase options as opposed to shares.
        """
        abool = False
        last_price = stock_strategy.get_stock_price(stock, cur_date, cur_time)
        symbol_list = [
            Holdings.get_options_symbol(
                stock, last_price, cur_date, stock_strategy.get_strikes_above(), stock_strategy.get_option_type()),
            Holdings.get_options_symbol(
                stock, last_price, cur_date, stock_strategy.get_strikes_above() + 1, stock_strategy.get_option_type())
        ]
        if not self.check_max_allocation(symbol_list[0], stock_strategy, cur_date, cur_time):
            Helper.log_warn(
                f"Portfolio currently has maximum allocation of {stock} on {cur_date} at {cur_time}")
            return abool

        # TODO Also, make all data saved to local database and attempt to fetch from there
        df_list = [Holdings.get_options_data(
            symbol_list[0]), Holdings.get_options_data(symbol_list[1])]
        if df_list[0] is None or df_list[1] is None:
            return abool
        num_contracts = stock_strategy.get_buying_allocation()
        holdings_price = Holdings.get_options_price(
            symbol_list[0], cur_date, cur_time) * 100 * num_contracts
        holdings_price2 = Holdings.get_options_price(
            symbol_list[1], cur_date, cur_time) * 100 * num_contracts
        total_price = holdings_price - holdings_price2
        buying_power = self.get_buying_power()
        if total_price < buying_power and total_price != 0.0:
            abool = True
            self.decrease_buying_power(total_price)
            self.add_holdings(symbol_list[0], num_contracts, holdings_price / 100,
                              Assets.Options, cur_date, df_list[0])
            Helper.log_info(
                f"\nBought (to open) {num_contracts} {symbol_list[0]} (${last_price} stock price) contract(s) on {cur_date} at {cur_time} for " +
                f"${holdings_price / 100} per contract.\n{stock_strategy}\n---")
            self.add_holdings(symbol_list[1], -1 * num_contracts, holdings_price2 / 100,
                              Assets.Options, cur_date, df_list[1])
            Helper.log_info(
                f"\nSold (to open) {-1 * num_contracts} {symbol_list[1]} (${last_price} stock price) contract(s) on " +
                f"{cur_date} at {cur_time} for ${holdings_price2 /100} per contract.\n{stock_strategy}\n---")
        else:
            abool = False
            Helper.log_warn(
                f"Insufficent buying power to buy {stock}\n{stock_strategy}\n---")
        return abool

    def buy(self, stock, stock_strategy, current_date, current_time):
        """
        Buys stock according to the stock strategy. If buying allocation (in stock strategy)
        is an int, it will buy that many shares. Otherwise, it'll buy that percent of the
        portfolio worth of the stock.

        Returns: True if the buy is succcessful. False otherwise
        """
        abool = False
        asset_type = stock_strategy.get_asset_type()
        if asset_type == Assets.Options:
            if stock_strategy.start_with_spreads():
                abool = self.buy_spreads(
                    stock, stock_strategy, current_date, current_time)
            else:
                abool = self.buy_options(
                    stock, stock_strategy, current_date, current_time)
            # print("buy after buy_options", abool)
        else:
            Helper.log_error("Not Implemented")
        return abool

    def sell(self, stock, stock_strategy, date, time):
        """
        Sells stock according to the stock_strategy
        """
        asset_type = stock_strategy.get_asset_type()
        abool = False
        if asset_type == Assets.Options:
            return self.sell_option(stock, date, time, stock_strategy)
        last_price = stock_strategy.get_stock_price(stock, date, time)
        current_value_holdings = self.get_current_allocation(
            stock, last_price, date, time)
        selling_allocation = stock_strategy.get_selling_allocation()
        if asset_type == Assets.Stocks:
            estimated_shares_gain = selling_allocation * current_value_holdings
            shares_to_sell = int(estimated_shares_gain // last_price)
            exact_shares_gain = shares_to_sell * last_price
        elif asset_type == Assets.Crypto:
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
            self.subtract_holdings(stock, shares_to_sell)
            Helper.log_info(
                f"Sold {shares_to_sell} {stock} shares on {date} at {time} for ${last_price} per share.")
        return abool

    def sell_option(self, option_name, current_date, current_time, strategy):
        """
        Sells the option according to the stock strategy
        """
        abool = False
        # change last price to get last options price at this date
        stock_name = re.match(r"\D+", option_name).group(0)
        position_info = self._current_holdings[stock_name].get_positions()[
            option_name]
        price_multiplier = 1
        if position_info[0] < 0:
            price_multiplier = -1
        # print("options_name", option_name)
        # print("current_date", current_date)
        # print("current_time", current_time)
        last_price = Holdings.get_options_price(
            option_name, current_date, current_time)
        num_contracts = strategy.get_selling_allocation()
        total_price = 100 * num_contracts * last_price * price_multiplier
        abool = True
        if last_price == 0.01:
            total_price = 0
        # Helper.log_info(f'total_price {total_price}')
        self.increase_buying_power(total_price)
        self.subtract_holdings(option_name, num_contracts * price_multiplier)
        if total_price > 0:
            Helper.log_info(
                f"\nSold (to close) {num_contracts} {option_name} (${last_price} stock price) contract(s) on {current_date}" +
                f" at {current_time} for ${last_price} per contract.\n{strategy}\n---")
        else:
            Helper.log_info(
                f"\nBought (to close) {num_contracts} {option_name}  (${last_price} stock price) contract(s) on {current_date} " +
                f"at {current_time} for ${last_price} per contract.\n{strategy}\n---")
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
