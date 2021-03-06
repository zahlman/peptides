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


    def sample(self, iterable, count=1):
        """Choose multiple values from the input, without replacement.
        `iterable` -> an iterable of values (not necessarily a sequence),
        or a mapping from values to (integer) counts. E.g. `{'x': 4, 'y': 2}`
        is equivalent to `['x', 'x', 'x', 'x', 'y', 'y']`.
        `count` -> the number of elements to choose.

        The values are returned in the order of appearance in the original
        `iterable`. This cannot be used to make a shuffled copy.
        """
        raise NotImplementedError # TODO


    def values(
        self, iterable, count=1, *,
        weights=(), base_weight=1, cumulative=False
    ):
        """Choose multiple values from the input, with replacement.
        `iterable` -> an iterable of values (not necessarily a sequence),
        or a mapping from values to weights.
        `count` -> the number of elements to choose.
        `weights` -> a sequence of weights to use for the first however many
        elements of the iterable. Must be empty when `iterable` is a mapping.
        `base_weight` -> the relative weight of elements beyond len(weights).
        Has no effect when `iterable` is a mapping.
        `cumulative` -> if set, the values in `weights` are treated as
        cumulative. Has no effect when `iterable` is a mapping.

        The values are returned as a dict, indicating how many times each
        element was chosen (only for those chosen at least once).
        """
        raise NotImplementedError # TODO


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
