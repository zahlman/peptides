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


@parametrize('args', [
    (None,), # bad types
    (1, 10, ()), # bad types for 3 args
    (1, 'a', 1),
    ('a', 10, 1),
    (1, 2, 3, 4), # too many args
    (inf, 0, -1), # start at infinity
    (-inf, 0, 1),
    (0, 3.3, 1), # type error although floating +/- infinity are allowed
])
def test_bad_types(args):
    with raises(TypeError):
        prange(*args)


@parametrize('args', [
    (0, 10, 'a'), # bad pattern string
    (0, 10, 0), # zero step size
    (0, 10, '0000') # must have a `1` in there
])
def test_bad_values(args):
    with raises(ValueError):
        prange(*args)


@parametrize('args', [
    (),
    (0,),
    (0, 1),
    (0, 1, 1),
    (0, 1, '1')
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


@parametrize('start,stop,step', [
    (3, -101, 7),
    (3, 100, 4),
    (3, 98, '0110101'),
    (1, 76, 1)
])
def test_consistency(start, stop, step):
    r = prange(start, stop, step)
    for i in r:
        assert i in r


@parametrize('args', [
    (),
    (0,),
    (5, 5),
    (2, 2, 1),
    (-7, -7, -3),
    (4, 4, '1101')
])
def test_empties(args):
    assert not list(prange(*args))


@parametrize('args', [
    (0, 10, '111'),
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
    (-23, -inf, '1101')
])
def test_inf_len(args):
    with raises(ValueError):
        len(prange(*args))
