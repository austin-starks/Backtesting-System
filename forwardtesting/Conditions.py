from abc import ABC, abstractmethod
import pandas as pd
import datetime
import re


class Condition(ABC):
    """
    Abstract class representing a condition

    This class is the parent class of all conditions. A condition is simply a predicate. The predicate determines whether a holding
    """

    def __init__(self, data, portfolio):
        self._data = data
        self._portfolio = portfolio
        self._holdings_to_sell = set()

    @abstractmethod
    def is_true(self):
        """
        Returns: True if this condition is true, False otherwise
        """
        return False

    def get_data(self):
        """
        Returns: The dataframe for this condition
        """
        return self._data

    def get_portfolio(self):
        """
        Returns: The portfolio for this condition
        """
        return self._portfolio

    def has_holdings_to_sell(self):
        """
        Returns: True if the condition has a list of holdings to sell. False otherwise
        """
        return False

    def delete_holding(self, holding):
        """
        Removes the holding from holdings to sell
        """
        self._holdings_to_sell.remove(holding)

    def get_holdings_to_sell(self):
        """
        Returns: the holdings to sell
        """
        return self._holdings_to_sell

    def clear_holdings_to_sell(self):
        """
        Removes all holdings from holdings to sell
        """
        self._holdings_to_sell = set()


class IsUpNPercent(Condition):
    """
    A class representing if a holding is down n percent.
    """

    def __init__(self, data, portfolio, n=0.5):
        super().__init__(data, portfolio)
        self._current_price = None
        self._n = n

    def has_holdings_to_sell(self):
        return True

    def is_true(self, current_date, current_time, current_price):
        # print('is true')
        abool = False
        portfolio = self.get_portfolio()
        holdings = portfolio.get_holdings()
        for holding in holdings:
            try:
                # print(strategies)
                # print(holding)
                # print(dataframe.head())
                today = current_price
                # print("today", today)
                initial_price = holding.get_initial_price()
                if initial_price < 0:
                    initial_price = initial_price * -1
                if abs(today / initial_price) >= self._n:
                    abool = True
                    self._holdings_to_sell.add(holding)
            except KeyError as e:
                print("Exception", e)
        return abool


class IsDownNPercent(Condition):
    """
    A class representing if a holding is down n percent.
    """

    def __init__(self, data, portfolio, n=0.5):
        super().__init__(data, portfolio)
        self._current_price = None
        self._n = n

    def has_holdings_to_sell(self):
        return True

    def is_true(self, current_date, current_time, current_price):
        # print('is true')
        abool = False
        portfolio = self.get_portfolio()
        holdings = portfolio.get_holdings()
        for holding in holdings:
            try:
                # print(strategies)
                # print(holding)
                # print(dataframe.head())
                today = current_price
                # print("today", today)
                initial_price = holding.get_initial_price()
                if initial_price < 0:
                    initial_price = initial_price * -1
                if abs(today / initial_price) < self._n:
                    abool = True
                    self._holdings_to_sell.add(holding)
            except KeyError as e:
                print(e)
        return abool


class TimePeriodCondition(Condition):
    """
    Condition parent class for conditions that has to deal with a stock's price
    within a time period.
    """

    def __init__(self, data, portfolio, sd=0, week_length=5):
        super().__init__(data, portfolio)
        self._standard_deviation = sd
        self._week_length = week_length
        self._changing_week_data = pd.DataFrame()
        self._changing_day_data = pd.DataFrame()

    def get_week_length(self):
        """
        Returns: the length of the time period to consider. Default: 5
        """
        return self._week_length

    def warm_up_data(self, today):
        """
        Warms-up changing_data to be prefilled with values.
        """
        if self._changing_week_data.empty:
            dataframe = self.get_data()
            if type(today) == pd._libs.tslibs.timestamps.Timestamp:
                today = today.strftime("%Y/%m/%d")
            arr = []
            i = 0
            # warm-up data with everyday starting from yesterday
            while len(arr) < self._week_length:
                i -= 1
                try:
                    arr.append(dataframe.iloc[i])
                except KeyError as e:
                    print(e)
            self._changing_week_data = pd.DataFrame(arr[::-1])

    def add_datapoint(self, datapoint):
        """
        Adds a datapoint to the changing data.
        """
        # print("before", self._changing_week_data)
        self._changing_week_data = self._changing_week_data[1:]
        # print('during', self._changing_week_data)
        self._changing_week_data = self._changing_week_data.append(datapoint)
        # print('after', self._changing_week_data)
        # print(datapoint)
        if len(self._changing_week_data) < self._week_length:
            assert False


class IsLowForPeriod(TimePeriodCondition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, data, portfolio, sd=0, week_length=5):
        super().__init__(data, portfolio, sd, week_length)

    def is_true_stocks(self, current_date, current_price):
        """
        Helper function for is_true for handling stock data
        """
        abool = False
        try:
            self.warm_up_data(current_date)
            # if current price < lowest price in dataframe, abool = True
            lowest_price = self._changing_week_data["Close"].min()
            # print("price + sd", current_price +
            #       (self._standard_deviation * self._changing_week_data["Close"].std()))
            # print("lowest price", lowest_price)
            print("current_price", current_price, type(current_price))
            if current_price < lowest_price + (self._standard_deviation * self._changing_week_data["Close"].std()):
                # print("lowest_price", lowest_price)
                # print((self._standard_deviation *
                #        self._changing_week_data["Close"].std()))
                abool = True
        except KeyError as e:
            print("Exception", e)
        return abool

    def is_true(self, current_date, current_price):
        """
        Returns: True if this condition is true, False otherwise
        """
        return self.is_true_stocks(current_date, current_price)


class IsHighForPeriod(TimePeriodCondition):
    """
    Condition: Is True if the stock is high for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, data, portfolio, sd=0, week_length=5):
        super().__init__(data, portfolio, sd, week_length)

    def is_true_stocks(self, current_date, current_price):
        """
        Helper function for is_true for handling stock data
        """
        abool = False
        try:
            self.warm_up_data(current_date)
            highest_price = self._changing_week_data["Close"].max()
            if current_price > highest_price + (self._standard_deviation * self._changing_week_data["Close"].std()):
                abool = True
        except KeyError:
            pass
        return abool

    def is_true(self, current_date, current_price):
        """
        Returns: True if this condition is true, False otherwise
        """
        return self.is_true_stocks(current_date, current_price)


class HasMoreBuyToOpen(Condition):
    """
    Condition: If the portfolio has more buy to open then it has sell to open of this stock.
    """

    def __init__(self, data, portfolio, asset):
        super().__init__(data, portfolio)
        self._asset = asset

    def has_holdings_to_sell(self):
        return True

    def is_true(self, current_date, current_time, *args):
        portfolio = self.get_portfolio()
        holdings = portfolio.get_holdings()
        posa_ends = 0
        nega_ends = 0
        for holding in holdings:
            num_holdings = holding.get_num_assets()
            holding_name = holding.get_underlying_name()
            if holding_name == self._asset:
                if num_holdings < 0:
                    nega_ends += 1
                else:
                    posa_ends += 1
        return posa_ends > nega_ends
