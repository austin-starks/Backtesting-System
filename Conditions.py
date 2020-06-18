from abc import ABC, abstractmethod
import pandas as pd
from datetime import date, timedelta
import re


class Condition(ABC):
    """
    Abstract class representing a condition

    This class is the parent class of all conditions. A condition is simply a predicate. The predicate determines whether a holding
    """

    def __init__(self, data, portfolio, sd=0):
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


class IsLowForPeriod(Condition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, data, portfolio, sd=0):
        super().__init__(data, portfolio)
        self._standard_deviation = sd
        self._week_length = 5
        self._changing_data = pd.DataFrame()

    def get_week_length(self):
        """
        Returns: the length of the time period to consider. Default: 5
        """
        return self._week_length

    def warm_up_data(self, datapoint):
        """
        Warms-p changing_data to be prefilled with values.
        """
        if len(self._changing_data) == 0:
            dataframe = self.get_data()
            today = datapoint.name
            date_arr = [int(x) for x in re.split(r'[\-]', today)]
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
            self._changing_data = pd.DataFrame(arr[::-1])

    def add_datapoint(self, datapoint):
        """
        Adds a datapoint to the changing data.
        """
        self._changing_data = self._changing_data[1:]
        self._changing_data.append(datapoint)

    def is_true(self, current_date, current_time):
        """
        Returns: True if this condition is true, False otherwise
        """
        # print(self._changing_data)
        dataframe = self.get_data()
        abool = True

        # print("is_true")
        abool = False
        try:
            today = dataframe.loc[str(current_date)]
            self.warm_up_data(today)
            current_price = round(
                today.loc[str(current_time)], 2)
            # if current price < lowest price in dataframe, abool = True
            lowest_price = self._changing_data["Close"].min()
            # print("price + sd", current_price +
            #       (self._standard_deviation * self._changing_data["Close"].std()))
            # print("lowest price", lowest_price)
            if current_price < lowest_price + (self._standard_deviation * self._changing_data["Close"].std()):
                abool = True
            if current_time.is_eod():
                self.add_datapoint(today)
        except KeyError:
            # print("Keyerror", str(current_date))
            pass
        return abool
