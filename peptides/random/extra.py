from collections.abc import Mapping
import sys


class GeneratorMixin:
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
