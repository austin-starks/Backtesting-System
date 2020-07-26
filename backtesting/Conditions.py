from abc import ABC, abstractmethod
import pandas as pd
from datetime import date, datetime, timedelta
import re
import sys
import State
import Helper


class Condition(ABC):
    """
    Abstract class representing a condition

    This class is the parent class of all conditions. A condition is simply a predicate. The predicate determines whether a holding
    """

    def __init__(self, portfolio):
        self._portfolio = portfolio
        self._asset_info = State.HoldingsStrategy.stock_info

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

    def __init__(self, portfolio, sd=0, week_length=5):
        super().__init__(portfolio)
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


class IsHighForPeriod(TimePeriodCondition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, portfolio, sd=0, week_length=5):
        super().__init__(portfolio, sd, week_length)

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
                highest_price = self._changing_week_data[key]["Close"].max()

                # print(current_date, current_price, key, highest_price,
                #       (self._standard_deviation * self._changing_week_data[key]["Close"].std()))
                if current_price > highest_price + (self._standard_deviation * self._changing_week_data[key]["Close"].std()):
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


class IsLowForPeriod(TimePeriodCondition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, portfolio, sd=0, week_length=5):
        super().__init__(portfolio, sd, week_length)

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


class NegaEndIsUpNPercent(Condition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, portfolio, target_percent_gain=0.6):
        super().__init__(portfolio)
        self._percent_gain = target_percent_gain

    def is_true(self, current_date, current_time):
        """
        Helper function for is_true for handling stock data
        """
        holdings = self._portfolio.get_holdings()
        abool = False
        # print("HERE", holdings)
        stocks_to_sell = dict()
        for holding_key in holdings:
            positions = holdings[holding_key].get_positions()
            for position_key in positions:
                position_info = positions[position_key]
                # if it is a nega-end
                if position_info[0] < 0:
                    current_price = State.Holdings.get_options_price(position_key,
                                                                     current_date, current_time)
                    original_price = position_info[1]
                    # print("current price", current_price,
                    #       "original price", original_price)
                    if current_price / original_price > self._percent_gain:
                        abool = True
                        stocks_to_sell[position_key] = (
                            current_date, current_time, current_price)

        if abool:
            return abool, stocks_to_sell
        else:
            return abool, None


class HasPosaEndThatsBooming(Condition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard
    deviations). False otherwise
    """

    def __init__(self, portfolio, target_percent_gain=0.6):
        super().__init__(portfolio)
        self._percent_gain = target_percent_gain

    def is_true(self, current_date, current_time):
        """
        Helper function for is_true for handling stock data
        """
        holdings = self._portfolio.get_holdings()
        # print("HERE", holdings)
        abool = False
        stocks_to_sell = dict()
        for holding_name in holdings:
            holdings_value_call = 0
            original_value_call = 0
            holdings_value_put = 0
            original_value_put = 0
            holding = holdings[holding_name]
            positions = holding.get_positions()
            nega_ends_calls, posa_ends_calls = 0, 0
            nega_ends_puts, posa_ends_puts = 0, 0
            highest_valued_call = None
            highest_valued_call_price = 0
            highest_valued_put = None
            highest_valued_put_price = 0
            for position in positions:
                price = State.Holdings.get_options_price(
                    position, current_date, current_time) * 100
                num_assets = positions[position][0]
                Helper.log_warn(f"pos_info {positions[position]}")
                if 'P' in position:
                    holdings_value_put += num_assets * price
                    original_value_put += num_assets * positions[position][1]
                    if num_assets > 0:
                        posa_ends_puts += 1
                    else:
                        nega_ends_puts += 1
                    if price > highest_valued_put_price:
                        highest_valued_put_price = price
                        highest_valued_put = position
                else:
                    holdings_value_call += num_assets * price
                    original_value_call += num_assets * positions[position][1]
                    if num_assets > 0:
                        posa_ends_calls += 1
                    else:
                        nega_ends_calls += 1
                    if price > highest_valued_call_price:
                        highest_valued_call_price = price
                        highest_valued_put = position
            if posa_ends_calls > nega_ends_calls and original_value_call != 0 and holdings_value_call / original_value_call >= self._percent_gain:
                Helper.log_warn(
                    f"highest_valued_call {holdings_value_call} posa {posa_ends_calls} nega {nega_ends_calls}")
                abool = True
                stocks_to_sell[position] = highest_valued_call
            if posa_ends_puts > nega_ends_puts and original_value_put != 0 and holdings_value_put / original_value_put >= self._percent_gain:
                Helper.log_warn(
                    f"highest_valued_put {holdings_value_put} posa {posa_ends_puts} nega {nega_ends_puts}")
                abool = True
                stocks_to_sell[position] = highest_valued_put
        if abool:
            return abool, stocks_to_sell
        else:
            return abool, None
