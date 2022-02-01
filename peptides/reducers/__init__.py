from functools import wraps as _wraps, partial as _partial

# Example code replacing the builtin `min`, `max`, `any`, `all` and `sum`
# functions to allow them to rely on dunder methods.
_original = {
    'len': len, # for range patch
    'min': min, 'max': max, 'any': any, 'all': all, 'sum': sum
}

_lookup = {}

def _register(t):
    def _do_register(func):
        _lookup[t, func.__name__] = func
        # Don't return `func`, since the name will be reused anyway
    return _do_register


def _get(name, x):
    try:
        return _lookup[type(x), name]
    except KeyError:
        try:
            return getattr(x.__class__, f'__{name}__')
        except AttributeError:
            return _original[name]


def _invoke(name, x):
    return _get(name, x)(x)


# patch len() for ranges
def len(x):
    try:
        return _original['len'](x)
    except OverflowError:
        if not isinstance(x, range):
            raise
        result, remainder = divmod(x.stop - x.start, x.step)
        if remainder != 0:
            result += 1
        return max(result, 0) # max() just in case


# helper for range reducers
def _add_stepcount(func):
    @_wraps(func)
    def wrapper(a_range):
        size = len(a_range)
        if size == 0:
            raise ValueError(f'{func.__name__}() of empty range')
        return func(a_range, size - 1)
    return wrapper


# min
@_register(range)
@_add_stepcount
def min(a_range, stepcount):
    start, step = a_range.start, a_range.step
    return start + (0 if step > 0 else step * stepcount)


# max
@_register(range)
@_add_stepcount
def max(a_range, stepcount):
    start, step = a_range.start, a_range.step
    return start + (0 if step < 0 else step * stepcount)


# any
@_register(range)
def any(a_range):
    # Range elements are distinct. So if there are at least two elements,
    # then one must be non-zero. If there is one, it must be the `.start`.
    count = len(a_range)
    return count > 1 or (count == 1 and a_range.start != 0)


# all
@_register(range)
def all(a_range):
    return 0 not in a_range


# sum
@_register(range)
@_add_stepcount
def sum(a_range, stepcount):
    first = a_range.start
    last = first + (a_range.step * stepcount)
    # Gauss' method.
    return (first + last) * (stepcount + 1) // 2


# Now that special implementations are registered, provide the names again.
for name in ('min', 'max', 'any', 'all', 'sum'):
    globals()[name] = _partial(_invoke, name)


# This would make it possible to implement, for example, a type that
# conceptually represents a floating-point range, as follows:
class frange:
    def __init__(low, high, include_low=True, include_high=False):
        self._low, self._high = low, high
        assert low <= high
        if low == high:
            assert include_low == include_high
        self._include_low = include_low
        self._include_high = include_high
        self._compare_low = low.__le__ if include_low else low.__lt__
        self._compare_high = high.__ge__ if include_high else high.__gt__


    def __contains__(self, value):
        return self._compare_low(value) and self._compare_high(value)


    # Explicitly call out these operations as not possible.
    def __iter__(self):
        raise NotImplementedError


    def __sum__(self):
        raise NotImplementedError


    # O(1) implementations of other reducers.
    def __all__(self):
        return 0.0 not in self

    def __any__(self):
        # Make sure the range isn't empty
        # and doesn't consist of a single zero value.
        if self._high == self._low:
            return self._include_low and self._low != 0.0
        # If it's a proper range, it must contain nonzero values.
        return True


    def __min__(self):
        if not self._include_low:
            raise ValueError("min is undefined")
        return self._low


    def __max__(self):
        if not self._include_high:
            raise ValueError("max is undefined")
        return self._high
