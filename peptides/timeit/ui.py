import argparse, importlib, os, sys, time
from . import autorange, default_timer, Timer


_default_trials = 5 # used for CLI and testing, not programmatically
_units = ((1.0, 'sec'), (1e-3, 'msec'), (1e-6, 'usec'), (1e-9, "nsec"))
_unit_names = tuple(u[1] for u in _units)


def _positive_int(s):
    result = int(s)
    if result < 1:
        raise ValueError('count must be at least 1')
    return result


epilog = """\
A multi-line statement may be given by specifying each line as a separate
argument; indented lines are possible by enclosing an argument in quotes and
using leading spaces. Multiple -s options are treated similarly.

If -n is not given, a suitable number of loops is calculated by trying
increasing numbers from the sequence 1, 2, 5, 10, 20, 50, ... until the
total time is at least 0.2 seconds.
"""


def _parse_args(args):
    parser = argparse.ArgumentParser(
        prog='timeit', description='TODO', epilog=epilog
    )
    parser.add_argument(
        '-i', '--iterations', type=_positive_int,
        help='number of iterations to run per timing trial\n(default: see below)'
    )
    parser.add_argument(
        '-u', '--unit', choices=_unit_names,
        help='set the output time unit (nsec, usec, msec, or sec)'
    )
    parser.add_argument(
        '-s', '--setup', nargs='+', default=['pass'],
        help="setup code to run before `stmt` (default 'pass').\n" +
        "Execution of this statement is NOT timed."
    )
    parser.add_argument(
        '-t', '--trials', type=_positive_int, default=_default_trials,
        help=f'how many timing trials to run (default {_default_trials})'
    )
    parser.add_argument(
        '-p', '--process', dest='timer', default=default_timer,
        help='timer to use (may be instantiated with no arguments)'
    )
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='display raw timing results; repeat for more digits precision'
    )
    parser.add_argument(
        'stmt', nargs='*', default=['pass'],
        help="statement to be timed (default 'pass')"
    )
    return parser.parse_args(args)


def _verbose_auto_number(timer, precision):
    def _callback(time_taken, number):
        s = '' if (number == 1) else 's'
        print(f"{number} loop{s} -> {time_taken:.{precision}g} secs")
        return time_taken, number
    count = timer.repeat(autorange(0.2), callback=_callback)[-1][1]
    print()
    return count


def _plain_auto_number(timer):
    return timer.repeat(autorange(0.2), callback='raw')[-1][1]


def format_time(precision, desired_name, dt):
    for scale, name in _units:
        if name == desired_name or (desired_name is None and dt >= scale):
            return f"{dt/scale:.{precision}g} {name}"
    assert False


def print_stats(timings, trials, iterations, precision, unit):
    best, worst = min(timings), max(timings)
    formatted_best = format_time(precision, unit, best)
    formatted_worst = format_time(precision, unit, worst)
    s = '' if iterations == 1 else 's'
    print(f"{iterations} loop{s}, best of {trials}: {formatted_best} per loop")
    if worst >= best * 4:
        msg_1 = "The test results are likely unreliable. The worst time"
        msg_2 = "was more than four times slower than the best time"
        warnings.warn_explicit(
            f"{msg_1} ({formatted_worst}) {msg_2} ({formatted_best}).",
            UserWarning, '', 0
        )


def run_verbose(timer, trials, iterations, precision, unit):
    try:
        if iterations is None:
            iterations = _verbose_auto_number(timer, precision)
        raw_timings = timer.repeat(trials, iterations=iterations, callback='raw')
    except:
        timer.print_exc()
        return 1
    print("raw times:", ", ".join(
        format_time(precision, unit, dt[0]) for dt in raw_timings
    ), end='\n\n')
    timings = [dt / count for dt, count in raw_timings]
    print_stats(timings, trials, iterations, precision, unit)
    return 0


def run_plain(timer, trials, iterations, precision, unit):
    try:
        if iterations is None:
            iterations = _plain_auto_number(timer)
        timings = timer.repeat(trials, iterations=iterations)
    except:
        timer.print_exc()
        return 1
    print_stats(timings, trials, iterations, precision, unit)
    return 0


def _parse_time_func(s):
    if callable(s):
        return s
    assert isinstance(s, str)
    instantiate = s.endswith('()')
    if instantiate:
        s = s[:-2]
    module_name, dot, func_name = s.rpartition('.')
    module = importlib.import_module(module_name)
    result = getattr(module, func_name)
    if instantiate:
        result = result()
    return result


def run(args):
    try:
        time_func = _parse_time_func(args.timer)
    except Exception as e:
        print('Timer lookup/creation failed:', file=sys.stderr)
        print(e, file=sys.stderr)
        return 2
    timer = Timer('\n'.join(args.stmt), '\n'.join(args.setup), time_func)
    trials, iterations, unit = args.trials, args.iterations, args.unit
    precision = 3 if args.verbose == 0 else 2 + args.verbose
    func = run_verbose if args.verbose else run_plain
    return func(timer, trials, iterations, precision, unit)


def main(args=None):
    """Main program, used when run as a script.

    `args` -> sequence of str
    The command line to be parsed (defaults to `sys.argv[1]`).

    Returns an exit code to be passed to `sys.exit` (0 indicates success).

    When an exception happens during timing, a traceback is printed to
    stderr and the return value is 1. If argument parsing with `argparse`
    fails, that return value is forwarded. Exceptions at other times
    (including the template compilation) are not caught.
    """
    try:
        args = _parse_args(args)
    except SystemExit as e:
        # Convert to a return code and then let the top-level code exit again.
        # This is mainly a hack for testing to work around argparse.
        return e.code
    # Include the current directory, so that local imports work (sys.path
    # contains the directory of this script, rather than the current
    # directory)
    sys.path.insert(0, os.curdir)
    return run(args)
