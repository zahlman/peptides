# standard library
from math import isclose
# test framework
from pytest import raises, mark
parametrize, xfail = mark.parametrize, mark.xfail
# local package
from peptides import random


# Test methods for things exposed at top level. It's inferred that
# the underlying classes work on some basic level. Note that we use explicit
# type checks because the interface should guarantee that it gives out
# specific exact types.
def test_bits():
    assert type(random.bits(1000)) is int
    assert [random.bits(0) for _ in range(10000)] == [0] * 10000
    # almost guaranteed :)
    assert set(random.bits(1) for _ in range(10000)) == {0, 1}
    assert all(0 <= random.bits(10) < 1024 for _ in range(10000))


def test_data():
    data = random.data(100)
    assert type(data) is bytes and len(data) == 100


def test_boolean():
    assert type(random.boolean()) is bool
    assert set(random.boolean() for _ in range(10000)) == {False, True}


def test_decimal():
    assert type(random.decimal()) is float
    assert all(0 <= random.decimal() < 1.0 for _ in range(10000))


@parametrize('start,end,t', (
    # integer values
    (1, 3, int),
    # If either type isn't int, don't give an int result.
    (0.0, 1, float), (1, 0.0, float), (0.0, 1.0, float), (1j, 0j, complex),
    (0, 1j, complex), (1j, 0, complex), (0.0, 1j, complex), (1j, 0.0, complex)
))
def test_between_types(start, end, t):
    assert type(random.between(start, end)) is t


@parametrize('start,end', (
    (1, 3), (1, -2), (-2, 1),
    (1.0, 3.0), (1.0, -2.0), (-2.0, 1.0)
))
def test_between_values(start, end):
    # the results should always be between the endpoints; with ints, both
    # endpoints should be selectable.
    results = [random.between(start, end) for _ in range(10000)]
    low, high = min(start, end), max(start, end)
    assert all(low <= r <= high for r in results)
    if isinstance(start, int) and isinstance(end, int):
        assert start in results and end in results


def test_between_complex():
    data = [random.between(2, 3j) for _ in range(10000)]
    assert all(isclose(r.real / 2 + r.imag / 3, 1) for r in data)


@xfail
def test_choose():
    random.choose([1, 2, 3])


@xfail
def test_sample():
    random.sample([1, 2, 3], 3)


@xfail
def test_values():
    random.values([1, 2, 3], 3)


@xfail
def test_shuffle():
    data = [1, 2, 3]
    seen = set()
    for i in range(10000):
        random.shuffle(data)
        seen.add(tuple(data))
    assert seen == {
        (1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)
    }


@xfail
def test_shuffled():
    data = [1, 2, 3]
    seen = set()
    for i in range(10000):
        shuffled = random.shuffled(data)
        assert shuffled == [1, 2, 3]
        seen.add(tuple(shuffled))
    assert seen == {
        (1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)
    }


# Very basic statistical test, should almost always pass
def test_bias():
    data = [random.boolean() for _ in range(10000)]
    assert 4500 < data.count(True) < 5500


# Tests of instance-specific stuff, to do with reproducibility.
def test_seeded():
    with raises(TypeError):
        rng = random.Seeded() # a seed must be provided
    rng = random.Seeded(0)
    state = rng.state
    with raises(TypeError):
        rng.state = None
    rng.state = state
    with rng.revert_state():
        first = [rng.decimal() for _ in range(100)]
    second = [rng.decimal() for _ in range(100)]
    third = [rng.decimal() for _ in range(100)]
    assert first == second
    assert second != third
