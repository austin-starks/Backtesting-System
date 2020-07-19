from abc import ABC, abstractmethod


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


class IsLowForWeek(Condition):
    """
    A class determining whether the stock is low for the week
    """

    def is_true(self, current_date, current_time):
        """
        Returns: True if the stock is low for the week, False otherwise 
        """
        for stock_name in self._asset_info:
            dataframe = self._asset_info[stock_name]
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
