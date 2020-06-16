from enum import IntFlag

class StockInfo(object):
    """
    A class representing a stock.

    This class holds information about a stock, including conditions on when to buy the stock, 
    when to sell the stock, and a dataframe of the data about the stock
    """
    def __init__(self, buying_conditions, selling_conditions, data):
        self._dataframe = data  
        self._buying_conditions = buying_conditions 
        self._selling_conditions = selling_conditions

class Portfolio(object):
    """
    A class representing a portfolio in a brokerage account. 

    This class holds information to simulate a portfolio. It includes information like the starting
    amount, the current portfolio holdings, and trading fees
    """
    def __init__(self, initial_value = 10000, current_value = 10000, margin = 1000, 
                current_holdings = [], past_holdings = [], trading_fees = .01):
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

class Resolution(IntFlag):
    """
    The resolution of data to backtest on.
    
    This Enum contains a list of data resolutions to analyze data from. The resolution can be in the magnitude of days
    (trading at open or at close), or can be in the timespan of minutes.
    """
    DAYS = 1