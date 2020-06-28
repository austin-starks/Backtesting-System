from abc import ABC, abstractmethod
import pandas as pd
from datetime import date, timedelta
import re


class Condition(ABC):
    """
    Abstract class representing a condition

    This class is the parent class of all conditions. A condition is simply a predicate. The predicate determines whether a holding
    """

    def __init__(self, data, portfolio):
        self._data = data
        self._portfolio = portfolio

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


class RollingStopCondition(Condition):
    """
    A class representing a rolling stop loss selling condition
    """

    def is_true(self):
        return False


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
