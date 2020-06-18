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
        self._last_purchase = None

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

    def buying_conditions_are_met(self, date, time):
        """
        Returns: True if buying conditions are met; False otherwise
        """
        abool = False
        # print(date >= date)
        # print("buying conditions are met", date)
        for condition in self._buying_conditions:
            if condition.is_true(date, time):
                abool = True
                break
        return abool and (self._last_purchase is None or self._last_purchase < date)

    def selling_conditions_are_met(self, date, time):
        """
        Returns: True if buying conditions are met; False otherwise
        """
        return True


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
