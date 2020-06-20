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


class StockStrategy(object):
    """
    A class representing a trading strategy for a stock.

    This class holds information about a particular strategy for a stock. It
    includes the buying/selling conditions for the stock, and how many days
    between deploying the strategy can it be deployed again
    """

    def __init__(self, name, data, buying_delay=1):
        self._name = name
        self._buying_conditions = []
        self._selling_conditions = []
        self._buying_allocation_for_stock = 0.05
        self._maximum_allocation_for_stock = 0.3
        self._data = data
        self._delay = buying_delay
        self._last_purchase = None
        self._last_price = None

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
        Sets last purchase to be a tuple of the last time this stock strategy was executed
        """
        self._last_purchase = (date, time)

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
        Returns: True if buying conditions are met; False otherwise
        """
        return True

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


class Portfolio(object):
    """
    A class representing a portfolio in a brokerage account.

    This class holds information to simulate a portfolio. It includes
    information like the starting amount, the current portfolio holdings,
    and trading fees
    """

    def __init__(self, initial_cash=100000,
                 current_holdings=[], past_holdings=[], trading_fees=.01):
        self._initial_value = initial_cash
        self._buying_power = initial_cash
        self._margin = 0  # will add margin later
        self._current_holdings = current_holdings
        self._past_holdings = past_holdings
        self._fees = trading_fees
        self._conditions = []

    def snapshot(self):
        """
        Returns: a snapshot of the portfolio
        """
        return f"Initial Value: {self._initial_value}\nCurrent Value: {self.get_portfolio_value()}" + \
            f"\nBuying Power: {self.get_buying_power()}\nCurrent Holdings: {self._current_holdings}\n" + \
            f"Percent Change from Start: {round((self.get_portfolio_value() - self._initial_value) / self._initial_value) * 100}%"

    def get_buying_power(self):
        """
        Returns: the current buying power of the portfolio
        """
        return self._buying_power

    def get_portfolio_value(self):
        """
        Returns: the value of all assets/cash in the portfolio
        """
        holdings_value = 0.0
        for holding in self._current_holdings:
            holdings_value += holding.get_value()
        return self.get_buying_power() + holdings_value

    def contains(self, stock):
        """
        Returns: True if this portfolio contains stock. False otherwise.
        """
        return stock in self._current_holdings

    def get_current_allocation(self, stock):
        """
        Returns: the percent of the portfolio that this stock makes up.
        """
        if self.contains(stock):
            holdings_value = 0.0
            for holding in self._current_holdings:
                if holding.get_name() == stock:
                    holdings_value += holding.get_value()
            return holdings_value/self.get_portfolio_value()
        else:
            return 0.0

    def add_holdings(self, stock, num_shares):
        """
        Adds the holdings to the portfolio
        """
        pass

    def decrease_buying_power(self, cost):
        """
        Decreases the buying power by cost
        """
        pass

    def buy(self, stock, stock_strategy, date, time):
        """
        Buys buying_allocation stock. If buying allocation is an int, it will buy that many shares. Otherwise, it'll
        buy that percent of the portfolio worth of the stock.

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
            dollars_to_spend = self.get_portfolio_value()*buying_allocation
            num_shares = dollars_to_spend // last_price
        else:
            Helper.log_error(f"Buying allocation should be an int or float")
        buying_power = self.get_buying_power()
        if self.get_current_allocation(stock) > max_allocation:
            Helper.log_warn(
                f"Portfolio currently has maximum allocation of {stock}")
        elif dollars_to_spend < buying_power:
            abool = True
            self.decrease_buying_power(dollars_to_spend)
            self.add_holdings(stock, num_shares)
        else:
            Helper.log_warn(f"Insufficent buying power to buy {stock}")
        return abool


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
