from functools import lru_cache as _cache, total_ordering as _cmp
from itertools import count
from math import inf
from operator import index as as_index


class _Pattern:
    # An immutable object representing a periodic sequence of integers.
    def __init__(self, steps):
        # The values are either positive and in ascending order, or negative
        # and in descending order. The last value indicates the size of the
        # repeating pattern.
        self._steps = tuple(steps)


    def __iter__(self):
        yield 0 # will be missed the first time around
        for offset in count(step = self._steps[-1]):
            for step in self._steps:
                yield offset + step


    @property
    def steps(self):
        return self._steps


    @property
    def size(self):
        return self._steps[-1]


    def _index(self, value):
        # helper search method
        assert abs(value) < abs(self.size)
        # handle candidate == 0 specially because of how self.steps is built
        if value == 0:
            return 0, True
        # since 0 <= abs(value) < abs(self.size),
        # the last check will always succeed, returning (self.size, False)
        for i, candidate in enumerate(self._steps, 1):
            if abs(candidate) >= abs(value):
                return i, candidate == value


    def __repr__(self):
        return f'{self.__class__.__qualname__}({self})'


    def __str__(self):
        return ', '.join(map(str, self._steps))


    def __contains__(self, index):
        before, found = self._index(index % self.size)
        return found


    def __getitem__(self, index):
        index = as_index(index) # slices not supported (yet)
        step_q, step_r = divmod(index - 1, len(self._steps))
        return step_q * self.size + self.steps[step_r]


    def __mul__(self, scalar):
        return _Pattern(s * scalar for s in self._steps)


    def count(self, distance):
        # How many elements in [0, distance)?
        q, r = divmod(distance, self.size)
        before, found = self._index(r)
        return q * len(self._steps) + before


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
    def __init__(self, start, stop, pattern):
        assert isinstance(start, int)
        assert int_or_inf(stop)
        self._start, self._stop, self._pattern = start, stop, pattern


    @property
    def start(self):
        return self._start


    @property
    def stop(self):
        return self._stop


    @property
    def steps(self):
        return self._pattern.steps


    def _signed(self, value):
        return -value if self.start > self.stop else value


    def _in_bounds(self, value):
        return 0 <= value <= abs(self.start - self.stop)


    def __len__(self):
        if isinstance(self.stop, float):
            raise ValueError('len() of unbounded range')
        return self._pattern.count(self.stop - self.start)


    def __contains__(self, value):
        try:
            as_int = int(value)
        except (ValueError, TypeError):
            return False
        if as_int != value: # e.g. non-integer float
            return False
        # Otherwise, find the corresponding index.
        distance = self._signed(value - self.start)
        if not self._in_bounds(distance):
            return False
        return distance in self._pattern


    def __getitem__(self, item):
        if isinstance(item, slice):
            raise NotImplementedError # TODO
        distance = self._pattern[as_index(item)]
        if not self._in_bounds(distance):
            raise IndexError('range object index out of range')
        return self.start + self._signed(distance)


    def __iter__(self):
        limit = abs(self.start - self.stop)
        for i in self._pattern:
            if abs(i) >= limit:
                return
            yield self.start + i


    def __str__(self):
        start, stop, steps = self.start, self.stop, self.steps
        if start == stop:
            return 'range()'
        if steps != (1,):
            args = (start, stop) + steps
            return f'range{args}'
        return f'range({stop})' if start == 0 else f'range({start}, {stop})'
    __repr__ = __str__


    # TODO: test these
    def __eq__(self, other):
        return self.start == other.start and self.stop == other.stop and self.steps == other.steps


    def __add__(self, scalar):
        return _Range(self.start + scalar, self.stop + scalar, self._pattern)


    def __sub__(self, scalar):
        return self + (-scalar)


    def __mul__(self, scalar):
        return _Range(
            self.start * scalar, self.stop * scalar, self._pattern * scalar
        )


    def __neg__(self): # unary -: reverse sign and orientation
        return self * -1


    #def __invert__(self): # unary ~: same range, all other steps
    # TODO



def range(*args):
    """range() -> (empty) range object
    range(stop) -> range object
    range(start, stop, *steps) -> range object

    More-or-less-drop-in replacement for built-in `range`.
    Can also be called with zero arguments to produce an empty range.
    Empty ranges also display specially.
    `steps` can be an ascending sequence of positive integers, or a
    descending sequence of negative integers. Defaults to (1,).

    Normalization:
    * The `start` value is normalized when using a string pattern that
      doesn't start with a one.
    * The `stop` value, when finite, is normalized to one plus the last
      value in range (equal to `stop` for empty ranges)."""
    # Unpack the args per built-in `range`.
    count = len(args)
    if count > 2:
        start, stop, *steps = args
    else:
        start, stop, steps = 0, 0, (1,)
        if count == 2:
            start, stop = args
        elif count == 1:
            stop, = args
    # Do a whole bunch of sanity checks.
    if not isinstance(start, int):
        raise TypeError('start must be an integer')
    if not int_or_inf(stop):
        raise TypeError('stop must be an integer or floating-point infinity')
    if not all(isinstance(step, int) for step in steps):
        raise TypeError('steps must all be integer')
    if 0 in steps:
        raise ValueError('steps may not be zero')
    step_direction = -1 if steps[0] < 0 else 1
    if not all(
        ((y - x) * step_direction) > 0
        for x, y in zip(steps, steps[1:])
    ):
        raise ValueError('invalid step sequence')
    # Normalize empty intervals. TODO: normalize other intervals too.
    range_direction = -1 if stop < start else 1
    if step_direction != range_direction:
        stop = start
    return _Range(start, stop, _Pattern(steps))
