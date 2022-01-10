from functools import wraps as _wraps, partial as _partial

# Example code replacing the builtin `min`, `max`, `any`, `all` and `sum`
# functions to allow them to rely on dunder methods.
_original = {
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
