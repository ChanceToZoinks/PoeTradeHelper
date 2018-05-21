class Observer:
    """Found here: https://stackoverflow.com/questions/1904351/python-observer-pattern-examples-tips"""

    _observers = []

    def __init__(self):
        self._observers.append(self)
        self._observables = {}

    def observe(self, event_name, callback):
        self._observables[event_name] = callback


class Event:
    """Found here: https://stackoverflow.com/questions/1904351/python-observer-pattern-examples-tips"""

    def __init__(self, name, data, autofire = True):
        self.name = name
        self.data = data
        if autofire:
            self.fire()

    def fire(self):
        for observer in Observer._observers:
            if self.name in observer._observables:
                observer._observables[self.name](self.data)