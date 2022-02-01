"""Replacement for standard library `random`, with an improved interface."""


class Random:
    # Import within the class to hide the names at top level
    from random import Random as _seeded
    try:
        from random import SystemRandom as _system
    except ImportError:
        _system = lambda: _seeded(None)
    

    def __init__(self, *args):
        if not args:
            self._implementation = Random._system()
            return
        seed, *args = args
        if args:
            count = len(args) + 1
            raise TypeError(f'Random expected at most 1 argument, got {count}')
        self._implementation = Random._seeded(seed)


    @property
    def state(self):
        try:
            return self._implementation.getstate()
        except NotImplementedError:
            return None


    @state.setter
    def state(self, value):
        try:
            self._implementation.setstate(value)
        except NotImplementedError:
            if value is not None:
                raise ValueError("State must be None for generator using system entropy source")


    def bits(self, amount):
        # For compatibility <3.9.
        if isinstance(amount, int) and amount == 0:
            return 0
        try:
            return self._implementation.getrandbits(amount)
        except ValueError: # Fix the message.
            raise ValueError("number of bits must be non-negative")


Random._implementation = Random()


def get_state():
    return Random._implementation.state


def set_state(state):
    Random._implementation.state = state


class revert_state:
    def __init__(self, instance=Random._implementation):
        self._instance = instance


    def __enter__(self):
        self._state = self._instance.state
        return self._instance


    def __exit__(self, exc_type, exc_value, traceback):
        self._instance.state = self._state


def bits(amount):
    return Random._implementation.bits(amount)
