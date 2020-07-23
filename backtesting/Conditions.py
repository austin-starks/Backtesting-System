from abc import ABC, abstractmethod
import pandas as pd
from datetime import date, datetime, timedelta
import re
import sys


class Condition(ABC):
    """
    Abstract class representing a condition

    This class is the parent class of all conditions. A condition is simply a predicate. The predicate determines whether a holding
    """

    def __init__(self, strategy):
        self._asset_info = strategy.get_asset_info()

    @abstractmethod
    def is_true(self):
        """
        Returns: True if this condition is true, False otherwise
        """
        return False


class TimePeriodCondition(Condition):
    """
    Condition parent class for conditions that has to deal with a stock's price
    within a time period.
    """

    def __init__(self, strategy, sd=0, week_length=5):
        super().__init__(strategy)
        self._standard_deviation = sd
        self._week_length = week_length
        self._changing_week_data = dict()
        self._changing_day_data = pd.DataFrame()

    def get_week_length(self):
        """
        Returns: the length of the time period to consider. Default: 5
        """
        return self._week_length

    def warm_up_data(self, stock_name, datapoint):
        """
        Warms-p changing_data to be prefilled with values.
        """
        if not stock_name in self._changing_week_data:
            dataframe = self._asset_info[stock_name]
            today = datapoint.name
            if type(today) == pd._libs.tslibs.timestamps.Timestamp:
                today = today.strftime("%Y/%m/%d")
            date_arr = [int(x) for x in re.split(r'[\-/]', today)]
            date_obj = date(date_arr[0], date_arr[1], date_arr[2])
            tmp_dict = {}
            i = 0
            while len(tmp_dict) < self._week_length:
                i -= 1
                delta = timedelta(days=i)
                tmp_date = (date_obj + delta).strftime("%Y-%m-%d")
                try:
                    tmp_dict[tmp_date] = dataframe.loc[tmp_date]
                except KeyError:
                    pass
            # print(tmp_dict)
            # print('index', tmp_dict.values())
            df = pd.DataFrame(tmp_dict.values(), index=tmp_dict.keys(),
                              columns=("Low", "Open", "Close", "High", "Volume", "Adj Close"))
            df.sort_index(inplace=True)
            self._changing_week_data[stock_name] = df
            # print(self._changing_week_data[stock_name])

    def add_datapoint(self, stock_name, datapoint):
        """
        Adds a datapoint to the changing data.
        """
        # print("before", self._changing_week_data)
        self._changing_week_data[stock_name] = self._changing_week_data[stock_name][1:]
        # print('during', self._changing_week_data)
        self._changing_week_data[stock_name] = self._changing_week_data[stock_name].append(
            datapoint)
        # print('after', self._changing_week_data)
        # print(datapoint)
        if len(self._changing_week_data[stock_name]) < self._week_length:
            assert False


class IsLowForPeriod(TimePeriodCondition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, strategy, sd=0, week_length=5):
        super().__init__(strategy, sd, week_length)

    def is_true(self, current_date, current_time):
        """
        Helper function for is_true for handling stock data
        """
        stocks_to_buy = dict()
        for key in self._asset_info:
            dataframe = self._asset_info[key]
            abool = False
            try:
                today = dataframe.loc[str(current_date)]
                self.warm_up_data(key, today)
                current_price = round(
                    today.loc[str(current_time)], 2)
                lowest_price = self._changing_week_data[key]["Close"].min()

                # print(current_date, current_price, key, lowest_price,
                #       (self._standard_deviation * self._changing_week_data[key]["Close"].std()))
                if current_price < lowest_price + (self._standard_deviation * self._changing_week_data[key]["Close"].std()):
                    abool = True
                    stocks_to_buy[key] = (
                        current_date, current_time, current_price)
                if current_time.is_eod():
                    # print("Is eod")
                    self.add_datapoint(key, today)
            except KeyError as e:
                print("Exception", e)
        if abool:
            return abool, stocks_to_buy
        else:
            return abool, None
