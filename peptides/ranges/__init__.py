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
    def __init__(self, start, stop, pattern):
        # Preprocessing ensures the range is directed from `start` to `stop`,
        # and that `start` is a definite endpoint except in the Z special case.
        self._start, self._stop, self._pattern = start, stop, pattern
        assert isinstance(start, (_Inf, int))
        assert isinstance(stop, (_Inf, int))
        assert isinstance(pattern, _Pattern)
        assert start is not Inf
        if start is -Inf:
            if stop is not Inf or str(pattern) != '1':
                raise ValueError("invalid start point for range")
            self._size = None
        elif stop in (Inf, -Inf):
            self._size = Inf
        else:
            self._size = abs(start - stop)


    @staticmethod
    def create(*args):
        # Unpack the args per built-in `range`.
        try:
            start, stop, step = args
        except ValueError:
            try:
                start, stop, step = (*args, 1)
            except ValueError:
                start, stop, step = (0, *args, 1)
        # Do a whole bunch of sanity checks.
        if not isinstance(step, int):
            raise TypeError('step must be an integer')
        if step == 0:
            raise ValueError('step cannot be zero')
        if not isinstance(start, (int, _Inf)):
            raise TypeError('start must be an integer or -Inf')
        if start is Inf:
            raise ValueError('start cannot be +Inf')
        if not isinstance(stop, (int, _Inf)):
            raise TypeError('stop must be an integer or +/-Inf')
        if step < 0 and start < stop:
            raise ValueError(
                'range with negative step must have start >= stop'
            )
        if step > 0 and start > stop:
            raise ValueError(
                'range with positive step must have start <= stop'
            )
        return Range(start, stop, _Pattern.from_step(step))


    def __contains__(self, value):
        try:
            as_int = int(value)
        except (ValueError, TypeError):
            return False
        if as_int != value: # e.g. non-integer float
            return False
        if self._start is -Inf: # represents all integers
            return True
        # Otherwise, find the corresponding index.
        start, stop = self._start, self._stop
        distance = value - start if stop > start else start - value
        if not 0 <= distance < self._size:
            return False
        return self._pattern[distance]


Z = Range(-Inf, Inf, _Pattern.from_step(1))
