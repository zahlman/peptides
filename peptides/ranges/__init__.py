from functools import total_ordering as _cmp


def _gcd(x, y):
    x, y = max(x, y), min(x, y)
    while y != 0:
        x, y = y, x % y
    return x


def _lcm(x, y):
    return (x * y) // _gcd(x, y)


class _Pattern:
    def __init__(self, count, sequence):
        self._count = count
        self._sequence = sequence


    @staticmethod
    def from_step(step):
        assert isinstance(step, int) and step != 0
        return _Pattern(abs(step), 1)


    @staticmethod
    def from_value(value):
        assert isinstance(value, int) and value > 1
        size = value.bit_length() - 1
        return _Pattern(size, value - (1 << size))


    @staticmethod
    def from_string(s):
        return _Pattern(len(s), int(s[::-1], 2))


    def __repr__(self):
        return f'{self.__class__.__qualname__}.from_string({self!r})'


    def __str__(self):
        bits = bin(self._sequence)[2:]
        return ((self._count - len(bits)) * '0' + bits)[::-1]


    def _padded_to(self, size):
        assert size % self._count == 0
        return sum(
            self._sequence << i
            for i in range(0, size, self._count)
        )


    def __and__(self, other):
        if not isinstance(other, _Pattern):
            return NotImplemented
        size = _lcm(self._count, other._count)
        return _Pattern(size, self._padded_to(size) & other._padded_to(size))


    def __getitem__(self, index):
        return bool(self._sequence & (1 << (index % self._count)))


@_cmp
class _Inf:
    def __new__(cls, sign):
        if not isinstance(sign, bool):
            raise TypeError
        if not hasattr(cls, '_instances'):
            cls._instances = [
                super().__new__(cls), super().__new__(cls)
            ]
        return cls._instances[sign]


    def __init__(self, sign):
        self._sign = sign


    def __neg__(self):
        return _Inf(not self._sign)


    def __gt__(self, other):
        if not isinstance(other, (_Inf, int)):
            return NotImplemented
        return False if self is other else self._sign


    def __str__(self):
        sign = '' if self._sign else '-'
        return f'{sign}Inf'
    __repr__ = __str__


Inf = _Inf(True)


class Range:
    """Replacement for builtin `range` that can represent unbounded ranges
    and sequences with fancier patterns."""


    # Not intended to be called directly.
    # Negative value for `pattern` indicates counting downward.
    # The high bit of the absolute value is ignored; the rest encode a
    # repeating pattern used to mask values starting at `start` and proceeding
    # to `stop`.
    def __init__(self, start, stop, pattern=3):
        if start is None:
            if stop is not None or pattern != 3:
                raise ValueError("`start` can only be None for Z")
        if pattern < 0:
            pattern = -pattern
            self._direction = -1
        else:
            self._direction = 1
        self._pattern_length = pattern.bit_length() - 1
        self._pattern = pattern - (1 << self._pattern_length)
        self._start = start
        self._size = None if stop is None else max(0, (stop - start) * self._direction)


    def __contains__(self, value):
        try:
            as_int = int(value)
        except (ValueError, TypeError):
            return False
        if as_int != value: # e.g. non-integer float
            return False
        if self._start is None: # represents all integers
            return True
        distance = (value - self._start) * self._direction
        if self._size is not None and distance >= self._size:
            return False
        if distance < 0:
            return False
        return bool(self._pattern & (1 << (distance % self._pattern_length)))

