from functools import lru_cache as _cache, total_ordering as _cmp
from math import inf


_range = range


def _gcd(x, y):
    x, y = max(x, y), min(x, y)
    while y != 0:
        x, y = y, x % y
    return x


def _lcm(x, y):
    return (x * y) // _gcd(x, y)


class _Pattern:
    def __init__(self, sequence):
        # `sequence` - an integer representing a repeating pattern of
        # sequence.bit_length() values - via its binary representation, from
        # least to most significant bit. It always ends in a true value; we
        # rotate the sequence in preprocessing such that the first set bit in
        # the input is moved to the end (ensuring that `bit_length` accurately
        # tells us the desired length).
        self._sequence = sequence


    @staticmethod
    def create(step):
        # return an instance and an offset.
        if isinstance(step, int):
            if step == 0:
                raise ValueError('step cannot be zero')
            return _Pattern(1 << (abs(step) - 1)), 0
        elif isinstance(step, str):
            # Avoid 0b prefixes.
            if any(c not in '01' for c in step):
                raise ValueError('invalid pattern string')
            # Normalize by swapping the first 1 to the end.
            count = step.find('1') + 1
            if not count:
                raise ValueError('pattern cannot be empty')
            step = step[count:] + step[:count]
            return _Pattern(int(step[::-1], 2)), count - 1
        else:
            raise TypeError('pattern must be int or string')


    @property
    def size(self):
        return self._sequence.bit_length()


    @property
    @_cache(None)
    def steps(self):
        result, bits, stride = [], self._sequence, 1
        while bits:
            if bits & 1:
                result.append(stride)
                stride = 0
            stride += 1
            bits >>= 1
        return result


    def __iter__(self):
        # The 0th value is always in the cycle, due to the normalization.
        value, cycle = 0, self.steps
        while True:
            for step in cycle:
                yield value
                value += step


    def __repr__(self):
        return f'{self.__class__.__qualname__}.create({str(self)!r})'


    def __str__(self):
        # The most significant bit stays at the front, because the 0th value
        # is always present in the sequence. The rest are reversed, indicating
        # what happens for the 1st value in the 1s place, etc.
        bits = bin(self._sequence)
        return bits[2] + bits[3:][::-1]


    def _padded_to(self, size):
        assert size % self._sequence.bit_length() == 0
        return sum(
            self._sequence << i
            for i in range(0, size, self._sequence.bit_length())
        )


    def __and__(self, other):
        if not isinstance(other, _Pattern):
            return NotImplemented
        size = _lcm(self.size, other.size)
        # Since the high bit is set in both inputs, it will be set
        # in both padded versions, and thus in the output sequence.
        return _Pattern(self._padded_to(size) & other._padded_to(size))


    def __getitem__(self, index):
        return bool(self._sequence & (1 << (index % self.size)))


def int_or_inf(x):
    if isinstance(x, int):
        return True
    if isinstance(x, float) and x in (inf, -inf):
        return True
    return False


class _Range:
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
        assert isinstance(start, int)
        assert int_or_inf(stop)
        assert isinstance(pattern, _Pattern)
        self._start, self._stop, self._pattern = start, stop, pattern


    def __contains__(self, value):
        try:
            as_int = int(value)
        except (ValueError, TypeError):
            return False
        if as_int != value: # e.g. non-integer float
            return False
        # Otherwise, find the corresponding index.
        start, stop = self._start, self._stop
        distance = value - start if stop > start else start - value
        if not 0 <= distance < abs(start - stop):
            return False
        return self._pattern[distance]


    def __iter__(self):
        start, stop = self._start, self._stop
        for i in self._pattern:
            if i >= abs(start - stop):
                return
            yield start + i if stop > start else start - i


    def __str__(self):
        start, stop, p = self._start, self._stop, self._pattern
        return 'range()' if start == stop else f"range({start}, {stop}, '{p}')"
    __repr__ = __str__


def range(*args):
    """range() -> (empty) range object
    range(stop) -> range object
    range(start, stop[, step]) -> range object

    More-or-less-drop-in replacement for built-in `range`.
    Can also be called with zero arguments to produce an empty range.
    Empty ranges also display specially.
    `step` can instead be a string pattern of ones and zeroes, indicating the
    (repeating) sequence of which values are in the range. In this case,
    the "direction" is inferred from `start` and `stop`.

    Normalization:
    * The `start` value is normalized when using a string pattern that
      doesn't start with a one.
    * The `stop` value, when finite, is normalized to one plus the last
      value in range (equal to `stop` for empty ranges)."""
    # Unpack the args per built-in `range`.
    count = len(args)
    if count > 3:
        raise TypeError('too many arguments for range() (at most 3 permitted)')
    start, stop, step = [
        (0, 0, 1),
        (0, *args, 1),
        (*args, 1),
        args
    ][len(args)]
    # Do a whole bunch of sanity checks.
    if isinstance(step, int):
        # Check for empty ranges and normalize.
        if (step < 0 and start < stop) or (step > 0 and start > stop):
            stop = start
        # TODO: normalize `stop` for other cases
    if not isinstance(start, int):
        raise TypeError('start must be an integer')
    pattern, offset = _Pattern.create(step)
    start += (offset if stop > start else -offset)
    if not int_or_inf(stop):
        raise TypeError('stop must be an integer or floating-point infinity')
    return _Range(start, stop, pattern)
