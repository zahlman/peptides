# standard library
import io, sys
from textwrap import dedent
# pytest
from pytest import fixture, mark, param, raises
skipif, parametrize = mark.skipif, mark.parametrize
del mark
# code under test
from peptides import timeit # test our version, not the standard library


# timeit's default number of per-test iterations and test repetitions.
DEFAULT_NUMBER = 1000000
DEFAULT_REPEAT = 5


# XXX: some tests are commented out that would improve the coverage but take a
# long time to run because they test the default number of loops, which is
# large.  The tests could be enabled if there was a way to override the default
# number of loops during testing, but this would require changing the signature
# of some functions that use the default as a default argument.


class FakeTimer:
    BASE_TIME = 42.0
    def __init__(self, seconds_per_increment=1.0):
        self.count = 0
        self.setup_calls = 0
        self.seconds_per_increment=seconds_per_increment
        timeit._fake_timer = self


    def __call__(self):
        return self.BASE_TIME + self.count * self.seconds_per_increment


    def inc(self):
        self.count += 1


    def setup(self):
        self.setup_calls += 1


    def wrap_timer(self, timer):
        """Records 'timer' and returns self as callable timer."""
        self.saved_timer = timer
        return self


@fixture
def fake_timer():
    yield FakeTimer()
    del timeit._fake_timer


def test_reindent_empty():
    assert timeit.reindent("", 0) == ""
    assert timeit.reindent("", 4) == ""


def test_reindent_single():
    assert timeit.reindent("pass", 0) == "pass"
    assert timeit.reindent("pass", 4) == "pass"


def test_reindent_multi_empty():
    assert timeit.reindent("\n\n", 0) == "\n\n"
    assert timeit.reindent("\n\n", 4) == "\n    \n    "


def test_reindent_multi():
    assert timeit.reindent("print()\npass\nbreak", 0) == "print()\npass\nbreak"
    assert (
        timeit.reindent("print()\npass\nbreak", 4) == 
        "print()\n    pass\n    break"
    )


def test_timer_invalid_stmt():
    with raises(ValueError):
        timeit.Timer(stmt=None)
    with raises(SyntaxError):
        timeit.Timer(stmt='return')
    with raises(SyntaxError):
        timeit.Timer(stmt='yield')
    with raises(SyntaxError):
        timeit.Timer(stmt='yield from ()')
    with raises(SyntaxError):
        timeit.Timer(stmt='break')
    with raises(SyntaxError):
        timeit.Timer(stmt='continue')
    with raises(SyntaxError):
        timeit.Timer(stmt='from timeit import *')
    with raises(SyntaxError):
        timeit.Timer(stmt='  pass')
    with raises(SyntaxError):
        timeit.Timer(stmt='  break', setup='while False:\n  pass')


def test_timer_invalid_setup():
    with raises(ValueError):
        timeit.Timer(setup=None)
    with raises(SyntaxError):
        timeit.Timer(setup='return')
    with raises(SyntaxError):
        timeit.Timer(setup='yield')
    with raises(SyntaxError):
        timeit.Timer(setup='yield from ()')
    with raises(SyntaxError):
        timeit.Timer(setup='break')
    with raises(SyntaxError):
        timeit.Timer(setup='continue')
    with raises(SyntaxError):
        timeit.Timer(setup='from timeit import *')
    with raises(SyntaxError):
        timeit.Timer(setup='  pass')


def test_timer_empty_stmt():
    timeit.Timer(stmt='')
    timeit.Timer(stmt=' \n\t\f')
    timeit.Timer(stmt='# comment')


fake_setup = "from peptides import timeit\ntimeit._fake_timer.setup()"
fake_stmt = "from peptides import timeit\ntimeit._fake_timer.inc()"


def run_timeit(fake_timer, stmt, setup, number=None, globals=None):
    t = timeit.Timer(stmt=stmt, setup=setup, timer=fake_timer,
            globals=globals)
    kwargs = {}
    if number is None:
        number = DEFAULT_NUMBER
    else:
        kwargs['number'] = number
    delta_time = t.timeit(**kwargs)
    assert fake_timer.setup_calls == 1
    assert fake_timer.count == number
    assert delta_time == number


# Takes too long to run in debug build.
#def test_timeit_default_iters(fake_timer):
#    run_timeit(fake_timer, fake_stmt, fake_setup)


def test_timeit_zero_iters(fake_timer):
    run_timeit(fake_timer, fake_stmt, fake_setup, number=0)


def test_timeit_few_iters(fake_timer):
    run_timeit(fake_timer, fake_stmt, fake_setup, number=3)


def test_timeit_callable_stmt(fake_timer):
    run_timeit(fake_timer, fake_timer.inc, fake_setup, number=3)


def test_timeit_callable_setup(fake_timer):
    run_timeit(fake_timer, fake_stmt, fake_timer.setup, number=3)


def test_timeit_callable_stmt_and_setup(fake_timer):
    run_timeit(fake_timer, fake_timer.inc, fake_timer.setup, number=3)


# Takes too long to run in debug build.
#def test_timeit_function():
#    delta_time = timeit.timeit(fake_stmt, fake_setup,
#            timer=FakeTimer())
#    assert delta_time == DEFAULT_NUMBER


def test_timeit_function_zero_iters():
    delta_time = timeit.timeit(fake_stmt, fake_setup, number=0,
            timer=FakeTimer())
    assert delta_time == 0


def test_timeit_globals_args():
    global _global_timer
    _global_timer = FakeTimer()
    t = timeit.Timer(stmt='_global_timer.inc()', timer=_global_timer)
    with raises(NameError):
        t.timeit(number=3)
    timeit.timeit(stmt='_global_timer.inc()', timer=_global_timer,
                  globals=globals(), number=3)
    local_timer = FakeTimer()
    timeit.timeit(stmt='local_timer.inc()', timer=local_timer,
                  globals=locals(), number=3)


def repeat(fake_timer, stmt, setup, repeat=None, number=None):
    t = timeit.Timer(stmt=stmt, setup=setup, timer=fake_timer)
    kwargs = {}
    if repeat is None:
        repeat = DEFAULT_REPEAT
    else:
        kwargs['repeat'] = repeat
    if number is None:
        number = DEFAULT_NUMBER
    else:
        kwargs['number'] = number
    delta_times = t.repeat(**kwargs)
    assert fake_timer.setup_calls == repeat
    assert fake_timer.count == repeat * number
    assert delta_times == repeat * [float(number)]


# Takes too long to run in debug build.
#def test_repeat_default(fake_timer):
#    repeat(fake_timerfake_stmt, fake_setup)


def test_repeat_zero_reps(fake_timer):
    repeat(fake_timer, fake_stmt, fake_setup, repeat=0)


def test_repeat_zero_iters(fake_timer):
    repeat(fake_timer, fake_stmt, fake_setup, number=0)


def test_repeat_few_reps_and_iters(fake_timer):
    repeat(fake_timer, fake_stmt, fake_setup, repeat=3, number=5)


def test_repeat_callable_stmt(fake_timer):
    repeat(fake_timer, fake_timer.inc, fake_setup,
            repeat=3, number=5)


def test_repeat_callable_setup(fake_timer):
    repeat(fake_timer, fake_stmt, fake_timer.setup,
            repeat=3, number=5)


def test_repeat_callable_stmt_and_setup(fake_timer):
    repeat(fake_timer, fake_timer.inc, fake_timer.setup,
            repeat=3, number=5)


# Takes too long to run in debug build.
#def test_repeat_function():
#    delta_times = timeit.repeat(fake_stmt, fake_setup,
#            timer=FakeTimer())
#    assertEqual(delta_times, DEFAULT_REPEAT * [float(DEFAULT_NUMBER)])


def test_repeat_function_zero_reps():
    delta_times = timeit.repeat(fake_stmt, fake_setup, repeat=0,
            timer=FakeTimer())
    assert delta_times == []


def test_repeat_function_zero_iters():
    delta_times = timeit.repeat(fake_stmt, fake_setup, number=0,
            timer=FakeTimer())
    assert delta_times == DEFAULT_REPEAT * [0.0]


def assert_exc_string(exc_string, expected_exc_name):
    exc_lines = exc_string.splitlines()
    assert len(exc_lines) > 2
    assert exc_lines[0].startswith('Traceback')
    assert exc_lines[-1].startswith(expected_exc_name)


def test_print_exc():
    s = io.StringIO()
    t = timeit.Timer("1/0")
    try:
        t.timeit()
    except:
        t.print_exc(s)
    assert_exc_string(s.getvalue(), 'ZeroDivisionError')


MAIN_DEFAULT_OUTPUT = "1 loop, best of 5: 1 sec per loop\n"


def run_main(capsys, seconds_per_increment=1.0, switches=None, timer=None):
    if timer is None:
        timer = FakeTimer(seconds_per_increment=seconds_per_increment)
    if switches is None:
        args = []
    else:
        args = switches[:]
    args.append(fake_stmt)
    # timeit.main() modifies sys.path, so save and restore it.
    orig_sys_path = sys.path[:]
    timeit.main(args=args, _wrap_timer=timer.wrap_timer)
    result = capsys.readouterr()
    sys.path[:] = orig_sys_path[:]
    return result.out, result.err


@parametrize('expected,options', (
    param(
        dedent("""\
            option --bad-switch not recognized
            use -h/--help for command line help
            """
        ),
        {'switches': ['--bad-switch']},
        id='bad_switch',
    ),
    param(
        "1 loop, best of 5: 5.5 sec per loop\n", 
        {'seconds_per_increment': 5.5},
        id='seconds'
    ),
    param(
        "50 loops, best of 5: 5.5 msec per loop\n", 
        {'seconds_per_increment': 0.0055},
        id='milliseconds'
    ),
    param(
        "100 loops, best of 5: 2.5 usec per loop\n", 
        {'seconds_per_increment': 0.0000025, 'switches':['-n100']},
        id='microseconds'
    ),
    param(
        "35 loops, best of 5: 2 sec per loop\n", 
        {'seconds_per_increment': 2.0, 'switches':['-n35']},
        id='fixed_iters'
    ),
    param(
        "CustomSetup\n" * DEFAULT_REPEAT + "35 loops, best of 5: 2 sec per loop\n",
        {
            'seconds_per_increment': 2.0,
            'switches':['-n35', '-s', 'print("CustomSetup")']
        },
        id='setup'
    ),
    param(
        "CustomSetup\n" * DEFAULT_REPEAT + "35 loops, best of 5: 2 sec per loop\n",
        {
            'seconds_per_increment': 2.0,
            'switches':['-n35', '-s', 'a = "CustomSetup"', '-s', 'print(a)']
        },
        id='multiple_setups'
    ),
    param(
        "1 loop, best of 9: 60 sec per loop\n",
        {'seconds_per_increment': 60.0, 'switches':['-r9']},
        id='fixed_reps'
    ),
    param(
        "1 loop, best of 1: 60 sec per loop\n",
        {'seconds_per_increment': 60.0, 'switches':['-r-5']},
        id='negative_reps'
    ),
))
def test_main_out(capsys, expected, options):
    out, err = run_main(capsys, **options)
    assert out == expected
    assert not err


@skipif(sys.flags.optimize >= 2, reason="need __doc__")
def test_main_help(capsys):
    out, err = run_main(capsys, switches=['-h'])
    # Note: It's not clear that the trailing space was intended as part of
    # the help text, but since it's there, check for it.
    assert out == timeit.__doc__ + ' '
    assert not err


def test_main_verbose(capsys):
    out, err = run_main(capsys, switches=['-v'])
    assert out == dedent("""\
            1 loop -> 1 secs

            raw times: 1 sec, 1 sec, 1 sec, 1 sec, 1 sec

            1 loop, best of 5: 1 sec per loop
        """)
    assert not err


def test_main_very_verbose(capsys):
    out, err = run_main(capsys, seconds_per_increment=0.000_030, switches=['-vv'])
    assert out == dedent("""\
            1 loop -> 3e-05 secs
            2 loops -> 6e-05 secs
            5 loops -> 0.00015 secs
            10 loops -> 0.0003 secs
            20 loops -> 0.0006 secs
            50 loops -> 0.0015 secs
            100 loops -> 0.003 secs
            200 loops -> 0.006 secs
            500 loops -> 0.015 secs
            1000 loops -> 0.03 secs
            2000 loops -> 0.06 secs
            5000 loops -> 0.15 secs
            10000 loops -> 0.3 secs

            raw times: 300 msec, 300 msec, 300 msec, 300 msec, 300 msec

            10000 loops, best of 5: 30 usec per loop
        """)
    assert not err


def test_main_with_time_unit(capsys):
    out, err = run_main(capsys, seconds_per_increment=0.003, switches=['-u', 'sec'])
    assert out == "100 loops, best of 5: 0.003 sec per loop\n"
    assert not err
    out, err = run_main(capsys, seconds_per_increment=0.003, switches=['-u', 'msec'])
    assert out == "100 loops, best of 5: 3 msec per loop\n"
    assert not err
    out, err = run_main(capsys, seconds_per_increment=0.003, switches=['-u', 'usec'])
    assert out == "100 loops, best of 5: 3e+03 usec per loop\n"
    assert not err
    # Test invalid unit input
    out, err = run_main(capsys, seconds_per_increment=0.003, switches=['-u', 'parsec'])
    assert err == "Unrecognized unit. Please select nsec, usec, msec, or sec.\n"
    assert not out


def test_main_exception(capsys):
    out, err = run_main(capsys, switches=['1/0'])
    assert not out
    assert_exc_string(err, 'ZeroDivisionError')


def test_main_exception_fixed_reps(capsys):
    out, err = run_main(capsys, switches=['-n1', '1/0'])
    assert not out
    assert_exc_string(err, 'ZeroDivisionError')


def autorange(seconds_per_increment=1/1024, callback=None):
    timer = FakeTimer(seconds_per_increment=seconds_per_increment)
    t = timeit.Timer(stmt=fake_stmt, setup=fake_setup, timer=timer)
    return t.autorange(callback)


def test_autorange():
    num_loops, time_taken = autorange()
    assert num_loops == 500
    assert time_taken == 500/1024


def test_autorange_second():
    num_loops, time_taken = autorange(seconds_per_increment=1.0)
    assert num_loops == 1
    assert time_taken == 1.0


def test_autorange_with_callback(capsys):
    def callback(a, b):
        print("{} {:.3f}".format(a, b))
    num_loops, time_taken = autorange(callback=callback)
    captured = capsys.readouterr()
    assert num_loops == 500
    assert time_taken == 500/1024
    expected = ('1 0.001\n'
                '2 0.002\n'
                '5 0.005\n'
                '10 0.010\n'
                '20 0.020\n'
                '50 0.049\n'
                '100 0.098\n'
                '200 0.195\n'
                '500 0.488\n')
    assert captured.out == expected
