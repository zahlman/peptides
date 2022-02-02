from abc import ABC, abstractmethod
from collections.abc import Mapping
from math import ldexp
import sys


"""Replacement for standard library `random`, with an improved interface."""


class Generator(ABC):
    """Abstract base class for random number generators."""
    @abstractmethod
    def bits(self, count):
        """Return a positive integer with the specified number of bits."""
        pass


    @abstractmethod
    def decimal(self):
        """Return a random floating-point value in [0.0, 1.0).
        All possible floats are used, but the PDF is uniform."""
        pass


    # Mixin methods.
    def data(self, count, byteorder=sys.byteorder):
        """Return the specified number of random bytes."""
        # It doesn't really matter which byte order we use for this.
        return self.bits(count * 8).to_bytes(count, byteorder=byteorder)


    def boolean(self):
        return bool(self.bits(1))


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


class BitsGenerator(Generator):
    """An implementation of Generator based on generating raw bits.
    A function is supplied to implement the `.bits` method, and `.decimal`
    is implemented in terms of that."""
    def __init__(self, get_bits):
        self._get_bits = get_bits


    def bits(self, count):
        # Accomodate functions that arbitrarily don't support count==0.
        return 0 if count == 0 else self._get_bits(count)


    def decimal(self):
        # Adapted from the documentation.
        mantissa = 0x10_0000_0000_0000 | self.bits(52)
        exponent = -53
        x = 0
        while not x:
            x = self.bits(32)
            exponent += x.bit_length() - 32
        return ldexp(mantissa, exponent)


class RealGenerator(Generator):
    """An implementation of Generator based on generating floating-point values.
    A function is supplied that returns a float value, which is normalized to
    implement `.decimal`. `bits` is implemented in terms of that, getting up
    to 53 bits per `decimal` call."""
    def __init__(self, get_float):
        self._get_float = get_float


    def bits(self, count):
        q, r = divmod(count, 53)
        if r:
            q, r = q + 1, 53 - r
        result = 0
        for _ in range(q):
            next_bits = self.decimal() * (1 << 53)
            result = (result << 53) | next_bits
        return result >> r


    def decimal(self):
        # No, we don't want `fmod` here; the result should be in [0, 1).
        # We expect values to be uniformly distributed whether or not
        # mantissas are, so use arithmetic to convert.
        return self._get_float() % 1


class Seeded(BitsGenerator):
    """A generator that uses a seed value to initialize a MT19937
    implementation and uses that as an entropy source. It also exposes
    the state of that internal generator as a property, and provides
    a context manager to revert the state after some operations."""
    # Import within the class to hide the names at top level
    from random import Random as _implementation
    def __init__(self, seed):
        self._implementation = Seeded._implementation(seed)
        super().__init__(self, self._implementation.getrandbits)


    @property
    def state(self):
        return self._implementation.getstate()


    @state.setter
    def state(self, value):
        self._implementation.setstate(value)


    class _revert_state:
        def __init__(self, instance):
            self._instance = instance


        def __enter__(self):
            self._state = self._instance.state
            return self._instance


        def __exit__(self, exc_type, exc_value, traceback):
            self._instance.state = self._state


    def revert_state(self): # context manager
        return Seeded._revert_state(self)


try:
    class SystemRandom(BitsGenerator):
        # Import within the class to hide the names at top level
        from random import SystemRandom as _implementation
        def __init__(self):
            self._implementation = SystemRandom._implementation()
            super().__init__(self._implementation.getrandbits)
except ImportError:
    # The name `SystemRandom` won't be available, and the core functions
    # will be implemented by a default-seeded instance. Even though it has
    # a state, we don't implement getstate()/setstate() - the user should
    # create an instance explicitly in order to have reproducible streams.
    Generator._default = Seeded(None)
else:
    # The core functions will be implemented by a SystemRandom instance,
    # which draws entropy from a hardware source. There is no state to
    # inspect or modify.
    Generator._default = SystemRandom()


for name in (
    'bits', 'data', 'boolean', 'decimal', 'between',
    'choose', 'sample', 'values', 'shuffle', 'shuffled'
):
    globals()[name] = getattr(Generator._default, name)
