from abc import ABCMeta, abstractmethod
from typing import Iterable

__all__ = ('Actioner',)


class Actioner(metaclass=ABCMeta):

    @abstractmethod
    def probe(self, obj, context) -> Iterable[str]:
        """Return an iterable of action names this actioner can perform given the object and
        the context"""

    @abstractmethod
    def do(self, action, obj, context):
        """Perform the action on the given object in the given context"""
