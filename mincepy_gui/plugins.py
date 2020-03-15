from abc import ABCMeta, abstractmethod
from typing import Iterable, Optional

__all__ = ('Actioner',)


class Actioner(metaclass=ABCMeta):

    @abstractmethod
    def probe(self, obj, context: dict) -> Optional[Iterable[str]]:
        """Return an iterable of action names this actioner can perform given the object and
        the context"""

    @abstractmethod
    def do(self, action, obj, context: dict):  # pylint: disable=invalid-name
        """Perform the action on the given object in the given context"""
