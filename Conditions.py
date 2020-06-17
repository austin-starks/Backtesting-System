from abc import ABC, abstractmethod


class Condition(ABC):
    """
    Abstract class representing a condition 

    This class is the parent class of all conditions. A condition is simply a predicate. The predicate determines whether a holding 
    """

    def __init__(self, data, date, sd=0):
        self._data = data
        self._date = date

    @abstractmethod
    def is_true(self):
        """
        Returns: True if this condition is true, False otherwise
        """
        return False


class IsLowForWeek(Condition):
    """
    Condition: Is True if the stock is low for the week (+/- n standard 
    deviations). False otherwise
    """

    def __init__(self, data, date, sd=0):
        super().__init__(data, date)
        self._standard_deviation = 0

    def is_true(self):
        """
        Returns: True if this condition is true, False otherwise
        """
        return True
