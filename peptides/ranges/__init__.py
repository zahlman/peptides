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

