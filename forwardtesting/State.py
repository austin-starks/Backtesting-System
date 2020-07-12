class Portfolio(object):
    """
    A class representing a portfolio in a brokerage account.

    This class holds information to simulate a portfolio. It includes
    information like the starting amount, the current portfolio holdings,
    and trading fees
    """

    def __init__(self, initial_cash=10000.00,
                 current_holdings=[], trading_fees=0.75):

        self._current_holdings = current_holdings
        self._buying_power = initial_cash
        self._initial_value = initial_cash
        self._fees = trading_fees

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
