from abc import ABC, abstractmethod
import pandas as pd
from datetime import date, timedelta
import re
import Helper
import State


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

    def is_true(self, current_date, current_time, *args):
        # print('is true')
        abool = False
        portfolio = self.get_portfolio()
        holdings = portfolio.get_holdings()
        strategies = portfolio.get_strategies()
        for holding in holdings:
            try:
                # print(strategies)
                # print(holding)
                dataframe = strategies[holding.get_name()]
                # print(dataframe.head())
                today = State.HoldingsStrategy.get_stock_price_static(
                    dataframe, current_date, current_time, holding.get_name())
                # print("today", today)
                initial_price = holding.get_initial_price()
                if initial_price < 0:
                    initial_price = initial_price * -1

                if abs(today / initial_price) < self._n:
                    abool = True
                    # Helper.log_warn("initial_price", initial_price)
                    # Helper.log_warn("today", today)
                    # Helper.log_warn('fraction', abs(
                    #     (today / initial_price)))
                    # Helper.log_warn('n', self._n)
                    # Helper.log_warn("SELLLLLLL")
                    # print("SELLLLLLL")
                    # print("SELLLLLLL")
                    self._holdings_to_sell.add(holding)
            except Exception as e:
                # print(dataframe)
                # print(today)
                print(e)
                pass
        return abool


class IsSoldToOpen(Condition):
    """
    A class representing if a holding is sold to open
    """

    def __init__(self, data, portfolio, n=0.5):
        super().__init__(data, portfolio)

    def has_holdings_to_sell(self):
        return True

    def is_true(self, current_date, current_time, *args):
        abool = False
        portfolio = self.get_portfolio()
        holdings = portfolio.get_holdings()
        for holding in holdings:
            num_holdings = holding.get_num_assets()
            if num_holdings < 0:
                abool = True
                self._holdings_to_sell.add(holding)
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

    def warm_up_data(self, datapoint):
        """
        Warms-p changing_data to be prefilled with values.
        """
        if self._changing_week_data.empty:
            dataframe = self.get_data()
            today = datapoint.name
            if type(today) == pd._libs.tslibs.timestamps.Timestamp:
                today = today.strftime("%Y/%m/%d")
            date_arr = [int(x) for x in re.split(r'[\-/]', today)]
            date_obj = date(date_arr[0], date_arr[1], date_arr[2])
            arr = []
            i = 0
            while len(arr) < self._week_length:
                i -= 1
                delta = timedelta(days=i)
                tmp_date = (date_obj + delta).strftime("%Y-%m-%d")
                try:
                    arr.append(dataframe.loc[tmp_date])
                except KeyError:
                    pass
            self._changing_week_data = pd.DataFrame(arr[::-1])

    def warm_up_data_crypto(self, datapoint):
        """
        Warms-up changing_data to be prefilled with values.
        """
        if self._changing_week_data.empty:
            dataframe = self.get_data()
            today = datapoint.name
            # print(dataframe.head())
            # print(today)
            if type(today) == pd._libs.tslibs.timestamps.Timestamp:
                today = today.strftime("%Y/%m/%d")
            date_arr = [int(x) for x in re.split(
                r'[\-/]', re.search(r"\d{4}[-/]\d+[-/]\d+", today)[0])]
            date_obj = date(date_arr[0], date_arr[1], date_arr[2])
            arr = []
            i = 0
            while len(arr) < self._week_length:
                i -= 1
                delta = timedelta(days=i)
                tmp_date = (date_obj + delta).strftime("%Y-%m-%d") + ' 12-AM'
                # print(tmp_date)
                arr.append(dataframe.loc[tmp_date])

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

    def is_true_stocks(self, current_date, current_time):
        """
        Helper function for is_true for handling stock data
        """
        dataframe = self.get_data()
        abool = False
        try:
            today = dataframe.loc[str(current_date)]
            self.warm_up_data(today)
            current_price = round(
                today.loc[str(current_time)], 2)
            # if current price < lowest price in dataframe, abool = True
            lowest_price = self._changing_week_data["Close"].min()
            # print("price + sd", current_price +
            #       (self._standard_deviation * self._changing_week_data["Close"].std()))
            # print("lowest price", lowest_price)
            if current_price < lowest_price + (self._standard_deviation * self._changing_week_data["Close"].std()):
                # print(current_price, lowest_price)
                abool = True
            if current_time.is_eod():
                self.add_datapoint(today)
        except KeyError:
            pass
        return abool

    def is_true_crypto(self, current_date, current_time):
        """
        Helper function for is_true for handling stock data
        """
        dataframe = self.get_data()
        abool = False
        date_time = str(current_date) + " " + str(current_time)
        today = dataframe.loc[date_time]
        self.warm_up_data_crypto(today)
        current_price = today.loc['Open']
        # if current price < lowest price in dataframe, abool = True
        lowest_price = self._changing_week_data["Low"].min()
        # print("price + sd", current_price +
        #       (self._standard_deviation * self._changing_week_data["Close"].std()))
        # print("lowest price", lowest_price)
        if current_price < lowest_price + (self._standard_deviation * self._changing_week_data["Open"].std()):
            # print(self._changing_week_data)
            # print("low, ", lowest_price)
            # print('std', self._standard_deviation *
                #   self._changing_week_data["Open"].std())
            # print("current, ", current_price)
            abool = True
        if current_time.is_eod():
            # print("is_eod", current_time)
            self.add_datapoint(today)
        return abool

    def is_true(self, current_date, current_time, assets):
        """
        Returns: True if this condition is true, False otherwise
        """
        if assets == 'stocks':
            return self.is_true_stocks(current_date, current_time)
        elif assets == 'crypto':
            return self.is_true_crypto(current_date, current_time)
        elif assets == "options":
            return self.is_true_stocks(current_date, current_time)


class IsHighForPeriod(TimePeriodCondition):
    """
    Condition: Is True if the stock is high for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, data, portfolio, sd=0, week_length=5):
        super().__init__(data, portfolio, sd, week_length)

    def is_true_stocks(self, current_date, current_time):
        """
        Helper function for is_true for handling stock data
        """
        dataframe = self.get_data()
        abool = False
        try:
            today = dataframe.loc[str(current_date)]
            self.warm_up_data(today)
            current_price = round(
                today.loc[str(current_time)], 2)
            highest_price = self._changing_week_data["Close"].max()
            if current_price > highest_price + (self._standard_deviation * self._changing_week_data["Close"].std()):
                abool = True
            if current_time.is_eod():
                self.add_datapoint(today)
        except KeyError:
            pass
        return abool

    def is_true_crypto(self, current_date, current_time):
        """
        Helper function for is_true for handling stock data
        """
        dataframe = self.get_data()
        abool = False
        date_time = str(current_date) + " " + str(current_time)
        today = dataframe.loc[date_time]
        self.warm_up_data_crypto(today)
        current_price = today.loc['Open']
        # if current price < lowest price in dataframe, abool = True
        highest_price = self._changing_week_data["High"].max()
        # print("price + sd", current_price +
        #       (self._standard_deviation * self._changing_week_data["Close"].std()))
        # print("lowest price", lowest_price)
        if current_price > highest_price + (self._standard_deviation * self._changing_week_data["Open"].std()):
            # print(current_price, highest_price, (self._standard_deviation *
            #                                      self._changing_week_data["Open"].std()))
            abool = True
        if current_time.is_eod():
            # print("is_eod", current_time)
            self.add_datapoint(today)
        return abool

    def is_true(self, current_date, current_time, assets):
        """
        Returns: True if this condition is true, False otherwise
        """
        # print("assets", assets)
        if assets == 'stocks':
            return self.is_true_stocks(current_date, current_time)
        elif assets == 'crypto':
            return self.is_true_crypto(current_date, current_time)
        elif assets == "options":
            return self.is_true_stocks(current_date, current_time)


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
