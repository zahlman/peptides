# standard library
import sys
# pytest
from pytest import fixture
# test infrastructure
from .infrastructure import parametrize, raises
# code under test
from peptides import timeit # test our version, not the standard library
from peptides.timeit.ui import main, _default_trials as DEFAULT_TRIALS


fake_setup = "_fake_timer.setup()"
fake_stmt = "_fake_timer.inc()"


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
def publish_fake_timer():
    timeit._fake_timer = FakeTimer()
    yield
    del timeit._fake_timer


def assert_exc_string(exc_string, expected_exc_name):
    exc_lines = exc_string.splitlines()
    assert len(exc_lines) > 2
    assert exc_lines[0].startswith('Traceback')
    assert exc_lines[-1].startswith(expected_exc_name)


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


# TIMEIT METHOD (AND FUNCTION)


_timeit_cases = (
    ('raw_zero_iters', [], 0, False, False, {'callback': 'raw'}, {}),
    ('few_iters', [], 3, False, False, {}, {}),
    ('raw_results', [], 3, False, False, {'callback': 'raw'}, {}),
    ('callable_stmt', [], 3, True, False, {}, {}),
    ('callable_setup', [], 3, False, True, {}, {}),
    ('callable_stmt_and_setup', [], 3, True, True, {}, {})
)


_method_options = (('method', [], False, {}), ('function', [], True, {}))


@parametrize(_method_options, 'use_function')
@parametrize(
    _timeit_cases, 'iterations', 'callable_stmt', 'callable_setup', 'kwargs'
)
def test_timeit_method(
    publish_fake_timer,
    iterations, callable_stmt, callable_setup, kwargs,
    use_function
):
    fake_timer = timeit._fake_timer
    stmt = fake_timer.inc if callable_stmt else fake_stmt
    setup = fake_timer.setup if callable_setup else fake_setup
    if use_function:
        result = timeit.timeit(
            iterations,
            stmt=stmt, setup=setup, timer=fake_timer, globals=None, **kwargs
        )
    else:
        timer = timeit.Timer(stmt, setup, fake_timer, None)
        result = timer.timeit(iterations, **kwargs)
    assert fake_timer.setup_calls == 1
    assert fake_timer.count == iterations
    if kwargs.get('callback', None) == 'raw':
        assert result == (float(iterations), iterations)
    else:
        assert result == 1.0


# REPEAT METHOD (AND FUNCTION)


def _do_repeat_method_test(
    stmt, setup, timer, trials, use_function, kwargs,
    trial_count, iteration_counts, raw
):
    if use_function:
        result = timeit.repeat(
            trials, stmt=stmt, setup=setup, timer=timer, **kwargs
        )
    else:
        t = timeit.Timer(stmt, setup, timer, None)
        result = t.repeat(trials, **kwargs)
    assert timer.setup_calls == trial_count
    assert timer.count == sum(iteration_counts)
    assert result == [
        (float(i), i) if raw else 1.0
        for i in iteration_counts
    ]


_repeat_int_cases = (
    ('zero_reps', [], 0, 1000000, False, False, False, {}),
    ('raw_zero_iters', [], 5, 0, False, False, True, {}),
    ('few_reps_and_iters', [], 3, 5, False, False, False, {}),
    ('raw_results', [], 3, 5, False, False, True, {}),
    ('callable_stmt', [], 3, 5, True, False, False, {}),
    ('callable_setup', [], 3, 5, False, True, False, {}),
    ('callable_stmt_and_setup', [], 3, 5, True, True, False, {})
)


@parametrize(_method_options, 'use_function')
@parametrize(
    _repeat_int_cases, 'trials', 'iterations',
    'callable_stmt', 'callable_setup', 'raw'
)
def test_repeat_method_int(
    publish_fake_timer,
    trials, iterations, callable_stmt, callable_setup, raw,
    use_function
):
    fake_timer = timeit._fake_timer
    kwargs = {'iterations': iterations}
    if raw:
        kwargs['callback'] = 'raw'
    _do_repeat_method_test(
        fake_timer.inc if callable_stmt else fake_stmt,
        fake_timer.setup if callable_setup else fake_setup,
        fake_timer, trials, use_function, kwargs,
        trials, [iterations] * trials, raw
    )


_repeat_range_cases = (
    ('zero_reps', [], (), False, False, False, {}),
    ('raw_zero_iters', [], (0, 0, 0, 0, 0), False, False, True, {}),
    ('few_reps_and_iters', [], range(1, 6), False, False, False, {}),
    ('raw_results', [], range(3, 6), False, False, True, {}),
    ('callable_stmt', [], range(3, 6), True, False, False, {}),
    ('callable_setup', [], range(3, 6), False, True, False, {}),
    ('callable_stmt_and_setup', [], range(3, 6), True, True, False, {})
)


@parametrize(_method_options, 'use_function')
@parametrize(
    _repeat_range_cases, 'trials',
    'callable_stmt', 'callable_setup', 'raw'
)
def test_repeat_method_int(
    publish_fake_timer,
    trials, callable_stmt, callable_setup, raw,
    use_function
):
    fake_timer = timeit._fake_timer
    _do_repeat_method_test(
        fake_timer.inc if callable_stmt else fake_stmt,
        fake_timer.setup if callable_setup else fake_setup,
        fake_timer, trials, use_function,
        {'callback': 'raw'} if raw else {},
        len(trials), trials, raw
    )


# AUTORANGE


def _autorange_callback(time, loops):
    print(f"{loops} {time:.3f}")
    return time, loops


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
    callback='raw', expected=''
)
def test_autorange(
    capsys, publish_fake_timer,
    seconds_per_call, num_loops, time_taken, callback, expected
):
    fake_timer = timeit._fake_timer
    fake_timer.seconds_per_call = seconds_per_call
    t = timeit.Timer(stmt=fake_stmt, setup=fake_setup, timer=fake_timer)
    results = t.repeat(timeit.autorange(0.2), callback=callback)
    if callback == 'raw':
        actual_time, actual_loops = results[-1]
        assert actual_time == time_taken
        assert actual_loops == num_loops
    result = capsys.readouterr()
    out, err = result.out, result.err
    assert out == expected
    assert not err


# PRINT_EXC METHOD


def test_print_exc(capsys):
    t = timeit.Timer("1/0")
    try:
        t.timeit(1)
    except:
        t.print_exc()
    assert_exc_string(capsys.readouterr().err, 'ZeroDivisionError')


# GLOBAL ARGUMENTS


def test_timeit_globals_args():
    # This time, we don't use the fixture because the code is testing
    # the use of globals and shouldn't be able to "cheat" by getting at
    # fake_timer instead.
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
    del _global_timer


# MAIN FUNCTION


_usage = """\
usage: timeit [-h] [-i ITERATIONS] [-u {sec,msec,usec,nsec}]
              [-s SETUP [SETUP ...]] [-c COUNT] [-t TIME_FUNC] [-v]
              [stmt [stmt ...]]"""
_error = "timeit: error:"
_bad_switch_msg = f"{_usage}\n{_error} unrecognized arguments: --bad-switch\n"
_invalid_unit = "argument -u/--unit: invalid choice:"
_parsec_choice = "'parsec' (choose from 'sec', 'msec', 'usec', 'nsec')"
_bad_unit_msg = f"{_usage}\n{_error} {_invalid_unit} {_parsec_choice}\n"
_invalid_trials = "argument -c/--count: invalid _positive_int value:"
_bad_reps_msg = f"{_usage}\n{_error} {_invalid_trials} '-5'\n"


_main_out_cases = (
    (
        'bad_switch', [], 1.0, ['--bad-switch'],
        _bad_switch_msg, {'verify': 'err'}
    ), (
        'seconds', [], 5.5, [],
        "1 loop, best of 5: 5.5 sec per loop\n", {}
    ), (
        'milliseconds', [], 0.0055, [],
        "50 loops, best of 5: 5.5 msec per loop\n", {}
    ), (
        'microseconds', [], 0.000_0025, ['-i100'],
        "100 loops, best of 5: 2.5 usec per loop\n", {}
    ), (
        'fixed_iters', [], 2.0, ['-i35'],
        "35 loops, best of 5: 2 sec per loop\n", {}
    ), (
        'setup', [], 2.0, ['-i35', '-s', 'print("CustomSetup")'],
        "CustomSetup\n" * DEFAULT_TRIALS +
        "35 loops, best of 5: 2 sec per loop\n", {}
    ), (
        'multiple_setups', [],
        2.0, ['-i35', '-s', 'a = "CustomSetup"', 'print(a)'],
        "CustomSetup\n" * DEFAULT_TRIALS +
        "35 loops, best of 5: 2 sec per loop\n", {}
    ), (
        'fixed_reps', [], 60.0, ['-c9'],
        "1 loop, best of 9: 60 sec per loop\n", {}
    ), (
        'negative_reps', [], 60.0, ['-c-5'],
        _bad_reps_msg, {'verify': 'err'}
    ),
    # We don't need to test -h; that's built-in argparse stuff
    (
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
        _bad_unit_msg, {'verify': 'err'}
    ), (
        'exception', [], 1.0, ['1/0'],
        'ZeroDivisionError', {'verify': 'exc'}
    ), (
        'exception_fixed_reps', [], 1.0, ['-i1', '1/0'],
        'ZeroDivisionError', {'verify': 'exc'}
    )
)


@parametrize(
    _main_out_cases, 'seconds_per_call', 'switches', 'expected', verify=None
)
def test_main_out(
    capsys, publish_fake_timer, expected, seconds_per_call, switches, verify
):
    fake_timer = timeit._fake_timer
    fake_timer.seconds_per_call = seconds_per_call
    timeflag = ['-t', 'peptides.timeit._fake_timer']
    args = timeflag + switches + ['--', fake_stmt]
    # timeit.main() modifies sys.path, so save and restore it.
    orig_sys_path = sys.path[:]
    main(args=args)
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
