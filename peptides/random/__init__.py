from abc import ABC, abstractmethod
from collections.abc import Mapping
from math import ldexp
import sys


"""Replacement for standard library `random`, with an improved interface."""


class Generator(ABC):
    @abstractmethod
    def bits(self, count):
        """Return a positive integer with the specified number of bits."""
        pass


    def data(self, count, byteorder=sys.byteorder):
        """Return the specified number of random bytes."""
        # It doesn't really matter which byte order we use for this.
        return self.bits(count * 8).to_bytes(count, byteorder=byteorder)


    def boolean(self):
        return bool(self.bits(1))


    def decimal(self):
        """Return a random floating-point value in [0.0, 1.0).
        All possible floats are used, but the PDF is uniform."""
        # Adaptedrom the documentation.
        mantissa = 0x10_0000_0000_0000 | self.bits(52)
        exponent = -53
        x = 0
        while not x:
            x = self.bits(32)
            exponent += x.bit_length() - 32
        return ldexp(mantissa, exponent)


    def between(self, start, end):
        """Return a random value from `start` to `end`.
        The end point is included if `start` and `end` are both integers;
        otherwise, it depends on rounding behaviour."""
        make_int = isinstance(start, int) and isinstance(end, int)
        size = end - start
        if make_int:
            size = (size if end >= start else -size) + 1
        raw = self.decimal() * size
        if make_int:
            raw = int(raw) if end >= start else -int(raw)
        return start + raw


    def choose(
        self, iterable, count=1, *,
        replace=None, base_weight=1, weights=(), cumulative=False
    ):
        """Choose multiple values from the input.
        `iterable` -> an iterable of values (not necessarily a sequence),
        or a mapping from values to (integer) counts. E.g. `{'x': 4, 'y': 2}`
        is equivalent to `['x', 'x', 'x', 'x', 'y', 'y']`.
        `count` -> the number of elements to choose.
        `replace` -> whether to choose with replacement. Required if `count`>1.
        weights -> a sequence of weights to use for the first however many
        elements of the iterable. Must be empty when `iterable` is a mapping.
        cumulative -> if set, the values in `weights` are treated as cumulative.
        Has no effect when `iterable` is a mapping.
        base_weight -> the relative weight of elements beyond len(weights).
        Has no effect when `iterable` is a mapping.

        The values are returned in the order of appearance in the original
        `iterable`. This cannot be used to make a shuffled copy.
        """
        raise NotImplementedError # TODO


    def sample(
        self, iterable, count=1, *,
        base_weight=1, weights=(), cumulative=False
    ):
        """Wrapper for `choose` without replacement."""
        return self.choose(
            iterable, count, replace=False,
            base_weight=base_weight, weights=weights, cumulative=cumulative
        )


    def values(
        self, iterable, count=1, *,
        base_weight=1, weights=(), cumulative=False
    ):
        """Wrapper for `choose` with replacement."""
        return self.choose(
            iterable, count, replace=True,
            base_weight=base_weight, weights=weights, cumulative=cumulative
        )


    def shuffle(self, a_list):
        """Shuffle a list in-place."""
        raise NotImplementedError


    def shuffled(self, iterable):
        """Get a shuffled copy of a sequence, shuffled output of an iterator,
        or shuffled data corresponding to a mapping (as described for `choose`).
        """
        if isinstance(iterable, Mapping):
            result = [k for k, v in iterable.items() for _ in range(v)]
        else:
            result = list(iterable)
        self.shuffle(result)
        return result


class Random(Generator):
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


def data(amount, byteorder=sys.byteorder):
    return Random._implementation.data(amount, byteorder)


def boolean():
    return Random._implementation.boolean()


def decimal():
    return Random._implementation.decimal()


def between(start, end):
    return Random._implementation.between(start, end)


def choose(
    iterable, count=1, *,
    replace=None, base_weight=1, weights=(), cumulative=False
):
    return Random._implementation.choose(
        iterable, count, replace=replace,
        base_weight=base_weight, weights=weights, cumulative=cumulative
    )


def sample(
    iterable, count=1, *,
    base_weight=1, weights=(), cumulative=False
):
    return Random._implementation.sample(
        iterable, count,
        base_weight=base_weight, weights=weights, cumulative=cumulative
    )


def values(
    iterable, count=1, *,
    base_weight=1, weights=(), cumulative=False
):
    return Random._implementation.values(
        iterable, count,
        base_weight=base_weight, weights=weights, cumulative=cumulative
    )


def shuffle(a_list):
    return Random._implementation.shuffle(a_list)


def shuffled(iterable):
    return Random._implementation.shuffled(iterable)
