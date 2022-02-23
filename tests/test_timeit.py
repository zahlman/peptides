# standard library
import sys
# pytest
from pytest import fixture, mark
slow, skipif = mark.slow, mark.skipif
del mark
# test infrastructure
from .infrastructure import parametrize, raises
# code under test
from peptides import timeit # test our version, not the standard library


DEFAULT_ITERATIONS = timeit.default_iterations
DEFAULT_TRIALS = timeit.default_trials
fake_setup = "from peptides import timeit\ntimeit._fake_timer.setup()"
fake_stmt = "from peptides import timeit\ntimeit._fake_timer.inc()"


class FakeTimer:
    BASE_TIME = 42.0
    def __init__(self):
        self.count = 0
        self.setup_calls = 0
        self.seconds_per_call = 1.0


    def __call__(self):
        return self.BASE_TIME + self.count * self.seconds_per_call


    def inc(self):
        self.count += 1


    def setup(self):
        self.setup_calls += 1


@fixture
def fake_timer():
    # Put the timer instance somewhere that can be accessed globally,
    # from dynamically compiled code, without worrying about globals.
    timeit._fake_timer = FakeTimer()
    yield timeit._fake_timer
    del timeit._fake_timer


def assert_exc_string(exc_string, expected_exc_name):
    exc_lines = exc_string.splitlines()
    assert len(exc_lines) > 2
    assert exc_lines[0].startswith('Traceback')
    assert exc_lines[-1].startswith(expected_exc_name)


def expected_time(expected_iterations, raw):
    return (float(expected_iterations), expected_iterations) if raw else 1.0


# TIMER CLASS CREATION


_timer_args_cases = (
    ('stmt_none', [], ValueError, {'stmt': None}),
    ('stmt_return', [], SyntaxError, {'stmt': 'return'}),
    ('stmt_yield', [], SyntaxError, {'stmt': 'yield'}),
    ('stmt_yield_from', [], SyntaxError, {'stmt': 'yield from ()'}),
    ('stmt_break', [], SyntaxError, {'stmt': 'break'}),
    ('stmt_continue', [], SyntaxError, {'stmt': 'continue'}),
    ('stmt_import', [], SyntaxError, {'stmt': 'from timeit import *'}),
    ('stmt_misaligned', [], SyntaxError, {'stmt': '  pass'}),
    (
        'stmt_misaligned_setup', [], SyntaxError,
        {'stmt': '  break', 'setup': 'while False:\n  pass'}
    ),
    ('stmt_empty', [], None, {'stmt': ''}),
    ('stmt_whitespace', [], None, {'stmt': ' \n\t\f'}),
    ('stmt_comment', [], None, {'stmt': '# comment'}),
    ('setup_none', [], ValueError, {'setup': None}),
    ('setup_return', [], SyntaxError, {'setup': 'return'}),
    ('setup_yield', [], SyntaxError, {'setup': 'yield'}),
    ('setup_yield_from', [], SyntaxError, {'setup': 'yield from ()'}),
    ('setup_break', [], SyntaxError, {'setup': 'break'}),
    ('setup_continue', [], SyntaxError, {'setup': 'continue'}),
    ('setup_import', [], SyntaxError, {'setup': 'from timeit import *'}),
    ('setup_misaligned', [], SyntaxError, {'setup': '  pass'})
)


@parametrize(_timer_args_cases, 'exc', stmt='pass', setup='pass')
def test_timer_args(stmt, setup, exc):
    with raises(exc):
        timeit.Timer(stmt=stmt, setup=setup)


# TIMEIT METHOD


_timeit_cases = (
    ('default_iters', [slow], False, False, {}, {}),
    ('raw_zero_iters', [], False, False, {'iterations': 0, 'raw': True}, {}),
    ('few_iters', [], False, False, {'iterations': 3}, {}),
    ('raw_results', [], False, False, {'iterations': 3, 'raw': True}, {}),
    ('callable_stmt', [], True, False, {'iterations': 3}, {}),
    ('callable_setup', [], False, True, {'iterations': 3}, {}),
    ('callable_stmt_and_setup', [], True, True, {'iterations': 3}, {})
)


@parametrize(
    _timeit_cases, 'callable_stmt', 'callable_setup', 'kwargs', globals=None
)
def test_timeit_method(
    fake_timer, callable_stmt, callable_setup, kwargs, globals
):
    stmt = fake_timer.inc if callable_stmt else fake_stmt
    setup = fake_timer.setup if callable_setup else fake_setup
    expected_iterations = kwargs.get('iterations', DEFAULT_ITERATIONS)
    timer = timeit.Timer(stmt, setup, fake_timer, globals)
    result = timer.timeit(**kwargs)
    assert fake_timer.setup_calls == 1
    assert fake_timer.count == expected_iterations
    raw = kwargs.get('raw', False)
    assert result == expected_time(expected_iterations, raw)


# REPEAT METHOD


_repeat_cases = (
    ('default', [slow], False, False, {}, {}), # about 3 seconds
    ('zero_reps', [], False, False, {'trials': 0}, {}),
    ('raw_zero_iters', [], False, False, {'iterations': 0, 'raw': True}, {}),
    (
        'few_reps_and_iters', [], False, False,
        {'trials': 3, 'iterations': 5}, {}
    ), (
        'raw_results', [], False, False,
        {'trials': 3, 'iterations': 5, 'raw': True}, {}
    ), (
        'callable_stmt', [], True, False, 
        {'trials': 3, 'iterations': 5}, {}
    ), (
        'callable_setup', [], False, True,
        {'trials': 3, 'iterations': 5}, {}
    ), (
        'callable_stmt_and_setup', [], True, True,
        {'trials': 3, 'iterations': 5}, {}
    )
)


@parametrize(
    _repeat_cases, 'callable_stmt', 'callable_setup', 'kwargs', globals=None
)
def test_repeat_method(
    fake_timer, callable_stmt, callable_setup, kwargs, globals
):
    stmt = fake_timer.inc if callable_stmt else fake_stmt
    setup = fake_timer.setup if callable_setup else fake_setup
    expected_iterations = kwargs.get('iterations', DEFAULT_ITERATIONS)
    trials = kwargs.get('trials', DEFAULT_TRIALS)
    t = timeit.Timer(stmt, setup, fake_timer, globals)
    result = t.repeat(**kwargs)
    assert fake_timer.setup_calls == trials
    assert fake_timer.count == trials * expected_iterations
    raw = kwargs.get('raw', False)
    assert result == trials * [expected_time(expected_iterations, raw)]


# AUTORANGE METHOD


def _autorange_callback(time, loops):
    print(f"{loops} {time:.3f}")


_autorange_text = (
    '1 0.001\n' +
    '2 0.002\n' +
    '5 0.005\n' +
    '10 0.010\n' +
    '20 0.020\n' +
    '50 0.049\n' +
    '100 0.098\n' +
    '200 0.195\n' +
    '500 0.488\n'
)


_autorange_cases = (
    ('fast', [], 1/1024, 500, 500/1024, {}),
    ('second', [], 1.0, 1, 1.0, {}),
    (
        'callback', [], 1/1024, 500, 500/1024,
        {'callback': _autorange_callback, 'expected': _autorange_text}
    )
)


@parametrize(
    _autorange_cases, 'seconds_per_call', 'num_loops', 'time_taken',
    callback=None, expected=''
)
def test_autorange(
    capsys, fake_timer,
    seconds_per_call, num_loops, time_taken, callback, expected
):
    fake_timer.seconds_per_call = seconds_per_call
    t = timeit.Timer(stmt=fake_stmt, setup=fake_setup, timer=fake_timer)
    actual_time, actual_loops = t.autorange(callback)
    assert actual_loops == num_loops
    assert actual_time == time_taken
    result = capsys.readouterr()
    out, err = result.out, result.err
    assert out == expected
    assert not err


# PRINT_EXC METHOD


def test_print_exc(capsys):
    t = timeit.Timer("1/0")
    try:
        t.timeit()
    except:
        t.print_exc()
    assert_exc_string(capsys.readouterr().err, 'ZeroDivisionError')


# TIMEIT AND REPEAT FUNCTIONS


_timeit_and_repeat_cases = (
    # about 0.6 seconds
    (
        'timeit_raw_default_iters', [slow], timeit.timeit, {'raw': True},
        (DEFAULT_ITERATIONS, DEFAULT_ITERATIONS), {}
    ), (
        'timeit_raw_zero_iters', [], timeit.timeit,
        {'iterations': 0, 'raw': True}, (0, 0), {}
    ), (
        'repeat_default', [slow], timeit.repeat, {}, # about 3 seconds
        DEFAULT_TRIALS * [1.0], {}
    ),
    ('repeat_zero_trials', [], timeit.repeat, {'trials': 0}, [], {}),
    (
        'repeat_raw_zero_iters', [], timeit.repeat,
        {'iterations': 0, 'raw': True},
        DEFAULT_TRIALS * [(0.0, 0)], {}
    )
)


@parametrize(_timeit_and_repeat_cases, 'func', 'kwargs', 'expected')
def test_functions(fake_timer, func, kwargs, expected):
    assert func(fake_stmt, fake_setup, timer=fake_timer, **kwargs) == expected


# GLOBAL ARGUMENTS


def test_timeit_globals_args():
    # This time, we don't use the fixture because the code is testing
    # the use of globals and shouldn't be able to "cheat" by getting at
    # timeit._fake_timer instead.
    global _global_timer
    _global_timer = FakeTimer()
    t = timeit.Timer(stmt='_global_timer.inc()', timer=_global_timer)
    with raises(NameError):
        t.timeit(iterations=3)
    timeit.timeit(
        stmt='_global_timer.inc()', timer=_global_timer,
        globals=globals(), iterations=3
    )
    local_timer = FakeTimer()
    timeit.timeit(
        stmt='local_timer.inc()', timer=local_timer,
        globals=locals(), iterations=3
    )


# MAIN FUNCTION


_main_out_cases = (
    (
        'bad_switch', [], 1.0, ['--bad-switch'],
        'option --bad-switch not recognized\n' +
        'use -h/--help for command line help\n', {'verify': 'err'}
    ), (
        'seconds', [], 5.5, [],
        "1 loop, best of 5: 5.5 sec per loop\n", {}
    ), (
        'milliseconds', [], 0.0055, [],
        "50 loops, best of 5: 5.5 msec per loop\n", {}
    ), (
        'microseconds', [], 0.000_0025, ['-n100'],
        "100 loops, best of 5: 2.5 usec per loop\n", {}
    ), (
        'fixed_iters', [], 2.0, ['-n35'],
        "35 loops, best of 5: 2 sec per loop\n", {}
    ), (
        'setup', [], 2.0, ['-n35', '-s', 'print("CustomSetup")'],
        "CustomSetup\n" * DEFAULT_TRIALS +
        "35 loops, best of 5: 2 sec per loop\n", {}
    ), (
        'multiple_setups', [],
        2.0, ['-n35', '-s', 'a = "CustomSetup"', '-s', 'print(a)'],
        "CustomSetup\n" * DEFAULT_TRIALS +
        "35 loops, best of 5: 2 sec per loop\n", {}
    ), (
        'fixed_reps', [], 60.0, ['-r9'],
        "1 loop, best of 9: 60 sec per loop\n", {}
    ), (
        'negative_reps', [], 60.0, ['-r-5'],
        "1 loop, best of 1: 60 sec per loop\n", {}
    ), (
        'help', [skipif(sys.flags.optimize >= 2, reason="need __doc__")],
        1.0, ['-h'], timeit.__doc__, {}
    ), (
        'verbose', [], 1.0, ['-v'],
        '1 loop -> 1 secs\n\n' +
        'raw times: 1 sec, 1 sec, 1 sec, 1 sec, 1 sec\n\n' +
        '1 loop, best of 5: 1 sec per loop\n', {}
    ), (
        'very_verbose', [], 0.000_030, ['-vv'],
        '1 loop -> 3e-05 secs\n' +
        '2 loops -> 6e-05 secs\n' +
        '5 loops -> 0.00015 secs\n' +
        '10 loops -> 0.0003 secs\n' +
        '20 loops -> 0.0006 secs\n' +
        '50 loops -> 0.0015 secs\n' +
        '100 loops -> 0.003 secs\n' +
        '200 loops -> 0.006 secs\n' +
        '500 loops -> 0.015 secs\n' +
        '1000 loops -> 0.03 secs\n' +
        '2000 loops -> 0.06 secs\n' +
        '5000 loops -> 0.15 secs\n' +
        '10000 loops -> 0.3 secs\n\n' +
        'raw times: 300 msec, 300 msec, 300 msec, 300 msec, 300 msec\n\n' +
        '10000 loops, best of 5: 30 usec per loop\n', {}
    ), (
        'time_sec', [], 0.003, ['-u', 'sec'],
        "100 loops, best of 5: 0.003 sec per loop\n", {}
    ), (
        'time_msec', [], 0.003, ['-u', 'msec'],
        "100 loops, best of 5: 3 msec per loop\n", {}
    ), (
        'time_usec', [], 0.003, ['-u', 'usec'],
        "100 loops, best of 5: 3e+03 usec per loop\n", {}
    ), (
        'time_nsec', [], 0.003, ['-u', 'nsec'],
        "100 loops, best of 5: 3e+06 nsec per loop\n", {}
    ), (
        'time_parsec', [], 0.003, ['-u', 'parsec'],
        'Unrecognized unit. Please select nsec, usec, msec, or sec.\n',
        {'verify': 'err'}
    ), (
        'exception', [], 1.0, ['1/0'],
        'ZeroDivisionError', {'verify': 'exc'}
    ), (
        'exception_fixed_reps', [], 1.0, ['-n1', '1/0'],
        'ZeroDivisionError', {'verify': 'exc'}
    )
)


@parametrize(
    _main_out_cases, 'seconds_per_call', 'switches', 'expected', verify=None
)
def test_main_out(
    capsys, fake_timer, expected, seconds_per_call, switches, verify
):
    fake_timer.seconds_per_call = seconds_per_call
    args = switches + [fake_stmt]
    # timeit.main() modifies sys.path, so save and restore it.
    orig_sys_path = sys.path[:]
    timeit.main(args=args, _wrap_timer=lambda timer:fake_timer)
    sys.path[:] = orig_sys_path[:]
    # Validate stdout and stderr results.
    result = capsys.readouterr()
    out, err = result.out, result.err
    if verify == 'exc':
        assert_exc_string(err, expected)
        assert not out
    elif verify == 'err':
        assert err == expected
        assert not out
    else:
        assert out == expected
        assert not err
