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

    def is_true(self):
        """
        Returns: True if the stock is low for the week, False otherwise 
        """
        return False
