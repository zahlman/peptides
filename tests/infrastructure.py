# standard library
from contextlib import contextmanager
# test framework
from pytest import mark, param, raises as _raises


@contextmanager
def does_not_raise():
    yield


def raises(exc):
    return _raises(exc) if exc else does_not_raise()


def make_parameter(args, required_count, defaults):
    test_name, marks, *required, optional = args
    assert len(required) == required_count
    for name, value in defaults.items():
        required.append(optional.get(name, value))
    return param(*required, id=test_name, marks=marks)


def my_parametrize(cases, *required_arg_names, **defaults):
    count = len(required_arg_names)
    assert count == len(set(required_arg_names))
    arg_names = ','.join(required_arg_names + tuple(defaults.keys()))
    return mark.parametrize(arg_names, tuple(
        make_parameter(args, count, defaults) for args in cases
    ))


def parametrize(*args, **kwargs):
    return mark.parametrize(*args, **kwargs)
