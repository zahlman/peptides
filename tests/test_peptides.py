# standard library
from math import inf
# test framework
from pytest import raises, mark
parametrize = mark.parametrize
# local package
from peptides import __version__
from peptides.ranges import range as prange


def test_version():
    assert __version__ == '0.1.0'


@parametrize('method', (list, len))
@parametrize('start,stop,step', [
    (1, 10, 1),
    (2, 17, 3),
    (2, 18, 3),
    (2, 19, 3),
    (3, 10, -1),
    (3, -10, -1),
    (3, -10, -2)
])
def test_simple_equivalents(start, stop, step, method):
    assert method(range(start, stop, step)) == method(prange(start, stop, step))


@parametrize('i,o', [
    ((), 'range()'),
    ((1,), 'range(1)'),
    ((1, 2), 'range(1, 2)'),
    ((1, 3, 2), 'range(1, 3, 2)'),
    ((1, 3, 1, 2), 'range(1, 3, 1, 2)')
])
def test_stringify(i, o):
    assert str(prange(*i)) == o


@parametrize('args', [
    (None,), # bad types
    (1, 10, 'a'), # bad types for 3 args
    (1, 'a', 1),
    ('a', 10, 1),
    (inf, 0, -1), # start at infinity
    (-inf, 0, 1),
    (0, 3.3, 1), # type error although floating +/- infinity are allowed
])
def test_bad_types(args):
    with raises(TypeError):
        prange(*args)


@parametrize('args', [
    (0, 10, 0), # zero step size
    (0, 10, 2, 1), # positive values must be in ascending order
    (0, 10, 1, -2), # definitely can't mix positive and negative
    (10, 0, -2, -1), # negative values must be in descending order
])
def test_bad_values(args):
    with raises(ValueError):
        prange(*args)


@parametrize('args', [
    (),
    (0,),
    (0, 10),
    (0, 10, 1),
    (0, 10, 1, 2) # equivalent to (0, 10, 2) but more complex internally
])
def test_good_args(args):
    prange(*args)
    assert True


def test_contents():
    r = prange(3, -101, -7)
    assert 3 in r
    assert -4 in r
    assert -95 in r
    assert 10 not in r
    assert 4 not in r
    assert 2 not in r
    assert -3 not in r
    assert -5 not in r
    assert -100 not in r
    assert -101 not in r
    assert -102 not in r


@parametrize('args', [
    (3, -101, 7),
    (3, 100, 4),
    (3, 98, 2, 3, 5, 7),
    (1, 76, 1)
])
def test_consistency(args):
    r = prange(*args)
    for i in r:
        assert i in r


@parametrize('args', [
    (),
    (0,),
    (5, 5),
    (2, 2, 1),
    (-7, -7, -3),
    (4, 4, 1, 2, 4)
])
def test_empties(args):
    assert not list(prange(*args))


@parametrize('args', [
    (0, 10, 1, 2, 3),
    (0, 10, 1),
    (0, 10),
    (10,)
])
def test_equivalent(args):
    assert list(prange(*args)) == list(range(10))


@parametrize('args', [
    (inf,),
    (0, inf),
    (34, -inf, -7),
    (-23, -inf, -1, -2, -4)
])
def test_inf_len(args):
    with raises(ValueError):
        len(prange(*args))


def test_operators():
    # These are pretty straightforward.
    p = prange(1, 10, 3)
    assert (p + 5) - 5 == p
    assert -p * -1 == p
