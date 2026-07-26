# executors/base.py

from abc import ABC, abstractmethod

class LanguageExecutor(ABC):

    extension: str

    @abstractmethod
    def build_command(self):
        pass