from abc import ABCMeta, abstractmethod
from typing import Iterable, Optional

__all__ = ('Actioner',)


class Actioner(metaclass=ABCMeta):

    @abstractmethod
    def probe(self, obj: object, context: dict) -> Optional[Iterable[str]]:
        """Return an iterable of action names this actioner can perform given the object and
        the context

        :param obj: object for which an action is being requested.  If this can do things with it
        then it should return a list of string for each of the actions
        :param context: the context that the action would be carried out in
        """

    @abstractmethod
    def do(self, action: str, obj: object, context: dict):  # pylint: disable=invalid-name
        """Perform the action on the given object in the given context

        :param action: the action to perform.  Will be one of the of the strings previously returned
        by probe()
        :param obj: the object to carry out the action on.
        :param context: the context that the action is being carried out in
        """
