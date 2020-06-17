from enum import IntFlag
import Conditions


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
        self._maximum_allocation_for_stock = 0.1
        self._data = data
        self._delay = buying_delay

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
        Returns: the buying conditions for this stock strategy
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


class Portfolio(object):
    """
    A class representing a portfolio in a brokerage account. 

    This class holds information to simulate a portfolio. It includes
    information like the starting amount, the current portfolio holdings, 
    and trading fees
    """

    def __init__(self, initial_value=10000, current_value=10000, margin=1000,
                 current_holdings=[], past_holdings=[], trading_fees=.01):
        self._initial_value = initial_value
        self._current_value = current_value
        self._margin = margin
        self._current_holdings = current_holdings
        self._past_holdings = past_holdings
        self._fees = trading_fees
        self._conditions = []

    def snapshot(self):
        """
        Returns: a snapshot of the portfolio
        """
        return f"Initial Value: {self._initial_value}\nCurrent Value: {self._current_value}" + \
            f"\nBuying Power: {self.get_buying_power()}\nCurrent Holdings: {self._current_holdings}\n" + \
            f"Percent Change from Start: {round((self._current_value - self._initial_value) / self._initial_value) * 100}%"

    def get_buying_power(self):
        """
        Returns: the current buying power of the portfolio
        """
        if self._current_holdings == []:
            return self._current_value + self._margin
        else:
            holdings_value = 0
            for holding in self._current_holdings:
                holdings_value += holding.value
            return self._current_value + self._margin - holdings_value

    def contains(self, stock):
        """
        Returns: True if this portfolio contains stock. False otherwise.
        """
        return stock in self._current_holdings


class Resolution(IntFlag):
    """
    The resolution of data to backtest on.

    This Enum contains a list of data resolutions to analyze data from. The resolution can be in the magnitude of days
    (trading at open or at close), or can be in the timespan of minutes.
    """
    DAYS = 1
