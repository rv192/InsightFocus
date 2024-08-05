from abc import ABC, abstractmethod

class QueueInterface(ABC):
    @abstractmethod
    def enqueue(self, item):
        pass

    @abstractmethod
    def dequeue(self):
        pass

    @abstractmethod
    def size(self):
        pass

    @abstractmethod
    def is_empty(self):
        pass