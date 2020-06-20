from enum import IntFlag
import Conditions
from datetime import date, timedelta
import Helper


class BacktestingState(object):
    """
    A class that repreents all of the state during a backtest.

    This class holds information about the portfolio and current strategies for
    a backtest
    """

    def __init__(self, portfolio, strategy_list):
        self._portfolio = portfolio
        self._strategy_list = strategy_list

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
        return self._portfolio.snapshot(date, time)


class Holdings(object):
    """
    A class representing a holding

    This class contains information about currently held assets including the cost, the type 
    of asset, and how much the person owns
    """

    def __init__(self, stock, num_assets, type_asset="Stock"):
        self._stock_name = stock
        self._num_assets = num_assets
        self._type = type_asset

    def __hash__(self):
        return hash(self._stock_name + self._type)

    def __eq__(self, other):
        return self._stock_name == other._stock_name and self._type == other._type

    def __str__(self):
        return "(" + self._stock_name + " | Num assets: " + str(self._num_assets) + ")"

    def __repr__(self):
        return "(" + self._stock_name + " | Num assets: " + str(self._num_assets) + ")"

    def get_name(self):
        """
        Returns: the name of the holdings
        """
        return self._stock_name

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


class StockStrategy(object):
    """
    A class representing a trading strategy for a stock.

    This class holds information about a particular strategy for a stock. It
    includes the buying/selling conditions for the stock, and how many days
    between deploying the strategy can it be deployed again
    """

    def __init__(self, name, data, buying_allocation=0.05, maximum_allocation=1.0, buying_delay=1,
                 selling_allocation=0.1):
        self._name = name
        self._buying_conditions = []
        self._selling_conditions = []
        self._buying_allocation_for_stock = buying_allocation
        self._maximum_allocation_for_stock = maximum_allocation
        self._selling_allocation_for_stock = selling_allocation
        self._data = data
        self._delay = buying_delay
        self._last_purchase = None
        self._last_price = None
        self._last_sale = None

    def get_dataframe(self):
        """
        Returns: the dataframe for this stock strategy
        """
        return self._data

    def get_stock_name(self):
        """
        Returns: the buying conditions for this stock strategy
        """
        return self._name

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

    def ackowledge_buy(self, date, time):
        """
        Sets last purchase to be a tuple of the last time this stock strategy bought an asset
        """
        self._last_purchase = (date, time)

    def ackowledge_sell(self, date, time):
        """
        Sets last sell to be a tuple of the last time this stock strategy sold an asset
        """
        self._last_sale = (date, time)

    def get_stock_price(self, date, time):
        """
        Returns: the current price of the stock at this date and time
        """
        return round(self._data.loc[str(date)].loc[str(time)], 2)

    def buying_conditions_are_met(self, date, time):
        """
        Returns: True if buying conditions are met; False otherwise
        """
        abool = False
        self._last_price = self.get_stock_price(date, time)
        for condition in self._buying_conditions:
            if condition.is_true(date, time):
                abool = True
                break
        return abool and (self._last_purchase is None or self._last_purchase[0] + timedelta(self._delay) <= date)

    def selling_conditions_are_met(self, date, time):
        """
        Returns: True if selling conditions are met; False otherwise
        """
        abool = False
        for condition in self._selling_conditions:
            if condition.is_true(date, time):
                abool = True
                break
        return abool

    def get_buying_allocation(self):
        """
        Returns: The buying allocatin for this strategy
        """
        return self._buying_allocation_for_stock

    def get_maximum_allocation(self):
        """
        Returns: The buying allocatin for this strategy
        """
        return self._maximum_allocation_for_stock

    def get_selling_allocation(self):
        """
        Returns: The buying allocatin for this strategy
        """
        return self._selling_allocation_for_stock

    @staticmethod
    def get_stock_price_static(df, date, time):
        """
        Returns: the current price of the stock at this date and time
        """
        i = 0
        while True:
            delta = timedelta(days=i)
            try:
                return round(df.loc[str(date + delta)].loc[str(time)], 2)
            except:
                i -= 1


class Portfolio(object):
    """
    A class representing a portfolio in a brokerage account.

    This class holds information to simulate a portfolio. It includes
    information like the starting amount, the current portfolio holdings,
    and trading fees
    """

    def __init__(self, initial_cash=100000.00,
                 current_holdings=[], past_holdings=[], trading_fees=0.75):
        self._initial_value = initial_cash
        self._buying_power = initial_cash
        self._margin = 0  # will add margin later
        self._current_holdings = current_holdings
        self._past_holdings = past_holdings
        self._fees = trading_fees
        self._conditions = []
        self._strategies = dict()

    def snapshot(self, date, time):
        """
        Returns: a snapshot of the portfolio
        """
        value = self.get_portfolio_value(date, time)
        percent_change = round(
            100 * (value - self._initial_value) / self._initial_value, 2)
        return f"Snapshot:\nInitial Value: {self._initial_value}\nCurrent Value: {value}" + \
            f"\nBuying Power: {self.get_buying_power()}\nCurrent Holdings: {self._current_holdings}\n" + \
            f"Percent Change from Start: {percent_change}%"

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
            holdings_df = self._strategies[holdings_name]
            holdings_price = StockStrategy.get_stock_price_static(
                holdings_df, date, time)
            holdings_value += holding.get_num_assets() * holdings_price
        return self.get_buying_power() + holdings_value

    def contains(self, stock):
        """
        Returns: True if this portfolio contains stock. False otherwise.
        """
        for holding in self._current_holdings:
            if holding.get_name() == stock:
                return True
        return False

    def get_current_allocation(self, stock, last_price, date, time):
        """
        Returns: the percent of the portfolio that this stock makes up.
        """
        if self.contains(stock):
            holdings_value = 0.0
            for holding in self._current_holdings:
                if holding.get_name() == stock:
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

    def add_holdings(self, stock, num_shares):
        """
        Adds the holdings to the portfolio
        """
        new_holding = Holdings(stock, num_shares)
        if new_holding in self._current_holdings:
            ind = self._current_holdings.index(new_holding)
            holding = self._current_holdings[ind]
            holding.add_shares(num_shares)
        else:
            self._current_holdings.append(new_holding)

    def subtract_holdings(self, stock, num_shares):
        """
        Subtravts the holdings to the portfolio
        """
        new_holding = Holdings(stock, num_shares)
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
        self._strategies[strategy.get_stock_name()] = strategy.get_dataframe()

    def buy(self, stock, stock_strategy, date, time):
        """
        Buys stock according to the stock strategy. If buying allocation (in stock strategy) 
        is an int, it will buy that many shares. Otherwise, it'll buy that percent of the 
        portfolio worth of the stock.

        Returns: True if the buy is succcessful. False otherwise
        """
        abool = False
        buying_allocation = stock_strategy.get_buying_allocation()
        max_allocation = stock_strategy.get_maximum_allocation()
        last_price = stock_strategy.get_stock_price(date, time)
        type_allo = type(buying_allocation)
        if type_allo == int:
            dollars_to_spend = buying_allocation * last_price
            num_shares = buying_allocation
        elif type_allo == float:
            dollars_to_spend = self.get_portfolio_value(
                date, time)*buying_allocation
            num_shares = int(dollars_to_spend // last_price)
        else:
            Helper.log_error(f"Buying allocation should be an int or float")
        buying_power = self.get_buying_power()
        total_price = num_shares*last_price
        if self.get_current_allocation(stock, last_price, date, time) + total_price > \
                max_allocation * self.get_portfolio_value(date, time):
            Helper.log_warn(
                f"Portfolio currently has maximum allocation of {stock}")
        elif total_price < buying_power:
            abool = True
            self.decrease_buying_power(total_price)
            self.add_holdings(stock, num_shares)
            self.add_strategy_data(stock_strategy)
        else:
            Helper.log_warn(f"Insufficent buying power to buy {stock}")
        return abool

    def sell(self, stock, stock_strategy, date, time):
        """
        Sells stock according to the stock_strategy
        """
        last_price = stock_strategy.get_stock_price(date, time)
        # print("last price", last_price)
        current_value_holdings = self.get_current_allocation(
            stock, last_price, date, time)
        selling_allocation = stock_strategy.get_selling_allocation()
        # print("selling allo", selling_allocation)
        estimated_shares_gain = selling_allocation * current_value_holdings
        shares_to_sell = int(estimated_shares_gain // last_price)
        exact_shares_gain = shares_to_sell * last_price
        # print('current_value_holdings', current_value_holdings)
        # print('estimated_shares_gain', estimated_shares_gain)
        # print('exact_shares_gain', exact_shares_gain)
        # print('shares to sell', shares_to_sell)
        self.increase_buying_power(exact_shares_gain)
        self.subtract_holdings(stock, shares_to_sell)
        return True


class Resolution(IntFlag):
    """
    The resolution of data to backtest on.

    This Enum contains a list of data resolutions to analyze data from. The resolution can be in the magnitude of days
    (trading at open or at close), or can be in the timespan of minutes.
    """
    DAYS = 2

    @staticmethod
    def time_init(resolution):
        if resolution == Resolution.DAYS:
            return 'Open'
        assert False

    @staticmethod
    def forward_time(time, resolution):
        if resolution == Resolution.DAYS:
            if time == 'Open':
                return 'Close'
            else:
                return "Open"
        assert False


class Time(object):
    """
    A class representing the current
    """
    resolution_dict = {Resolution.DAYS: ["Open", "Close"]}

    def __init__(self, resolution):
        self._time = Time.resolution_dict[resolution]
        self._time_index = 0

    def forward_time(self):
        self._time_index += 1
        self._time_index %= 2

    def __str__(self):
        return self._time[self._time_index]

    def __repr__(self):
        return self._time[self._time_index]

    def is_eod(self):
        # print("time index", self._time_index,
        #       "len(self._time) - 1", len(self._time) - 1)
        return self._time_index == len(self._time) - 1
