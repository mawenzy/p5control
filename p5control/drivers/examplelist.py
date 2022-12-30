"""
Test driver to make sure every connection gets the same instance
"""
from .basedriver import BaseDriver

class ExampleList(BaseDriver):
    def __init__(self, name):
        self._name = name
        self._list = []

        self.refresh_delay = 0.5

    def get_list(self):
        return self._list
    
    def add(self, item):
        self._list.append(item)
