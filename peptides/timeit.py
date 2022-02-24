#! /usr/bin/python3.8

"""Tool for measuring execution time of small code snippets.

This module attempts to minimize overhead associated with the timing loop,
and avoid common traps in interpreting the results. The overhead is still
non-zero, and the code here doesn't try to hide that when reporting results.
To measure the timing overhead, try invoking the program without arguments.

Library usage: see the Timer class.

Command-line usage: see `timeit -h`.

Classes:

    Timer

Functions:

    autorange(float) -> generator[int]
    default_timer() -> float
    repeat(string, string) -> list
    timeit(string, string) -> float
"""


import argparse, gc, itertools, linecache, os, sys, time, traceback, warnings
from .generator_feedback import feedback


__all__ = ["Timer", "autorange", "default_timer", "repeat", "timeit"]


dummy_src_name = "<timeit-src>"
default_timer = time.perf_counter


_default_trials = 5 # used for CLI and testing, not programmatically
_globals = globals
_units = ((1.0, 'sec'), (1e-3, 'msec'), (1e-6, 'usec'), (1e-9, "nsec"))
_unit_names = tuple(u[1] for u in _units)


# Don't change the indentation of the template; the reindent() calls
# in Timer.__init__() depend on setup being indented 4 spaces and stmt
# being indented 8 spaces.
template = """\
def inner(_it, _timer{init}):
    {setup}
    _t0 = _timer()
    for _i in _it:
        {stmt}
        pass
    _t1 = _timer()
    return _t1 - _t0
"""


def _reindent(src, indent):
    """Helper to reindent a multi-line statement."""
    return src.replace("\n", "\n" + " "*indent)


class Timer:
    """Class for timing execution speed of small code snippets.

    The constructor takes a statement to be timed, an additional
    statement used for setup, and a timer function.  Both statements
    default to 'pass'; the timer function is platform-dependent (see
    module doc string).  If 'globals' is specified, the code will be
    executed within that namespace (as opposed to inside timeit's
    namespace).

    To measure the execution time of the first statement, use the
    timeit() method.  The repeat() method is a convenience to call
    timeit() multiple times and return a list of results.

    The statements may contain newlines, as long as they don't contain
    multi-line string literals.
    """
    def __init__(
        self, stmt="pass", setup="pass", timer=default_timer, globals=None
    ):
        """Constructor.  See class doc string."""
        self.timer = timer
        local_ns = {}
        global_ns = _globals() if globals is None else globals
        init = ''
        if isinstance(setup, str):
            # Check that the code can be compiled outside a function
            compile(setup, dummy_src_name, "exec")
            stmtprefix = setup + '\n'
            setup = _reindent(setup, 4)
        elif callable(setup):
            local_ns['_setup'] = setup
            init += ', _setup=_setup'
            stmtprefix = ''
            setup = '_setup()'
        else:
            raise ValueError("setup is neither a string nor callable")
        if isinstance(stmt, str):
            # Check that the code can be compiled outside a function
            compile(stmtprefix + stmt, dummy_src_name, "exec")
            stmt = _reindent(stmt, 8)
        elif callable(stmt):
            local_ns['_stmt'] = stmt
            init += ', _stmt=_stmt'
            stmt = '_stmt()'
        else:
            raise ValueError("stmt is neither a string nor callable")
        src = template.format(stmt=stmt, setup=setup, init=init)
        self.src = src  # Save for traceback display
        code = compile(src, dummy_src_name, "exec")
        exec(code, global_ns, local_ns)
        self.inner = local_ns["inner"]


    def print_exc(self, file=None):
        """Helper to print a traceback from the timed code.

        Typical use:

            t = Timer(...)       # outside the try/except
            try:
                t.timeit(...)    # or t.repeat(...)
            except:
                t.print_exc()

        The advantage over the standard traceback is that source lines
        in the compiled template will be displayed.

        The optional file argument directs where the traceback is
        sent; it defaults to sys.stderr.
        """
        if self.src is not None:
            linecache.cache[dummy_src_name] = (
                len(self.src), None, self.src.split("\n"), dummy_src_name
            )
        # else the source is already stored somewhere else
        traceback.print_exc(file=file)


    def timeit(self, iterations, *, callback=None):
        """Time several executions of the main statement.

        To be precise, this executes the setup statement once, and
        then returns the time it takes to execute the main statement
        a number of times, as a float measured in seconds.  The
        argument is the number of times through the loop, defaulting
        to one million.  The main statement, the setup statement and
        the timer function to be used are passed to the constructor.
        """
        it = itertools.repeat(None, iterations)
        gcold = gc.isenabled()
        gc.disable()
        try:
            timing = self.inner(it, self.timer)
        finally:
            if gcold:
                gc.enable()
        if callback is None:
            return timing / iterations
        elif callback == 'raw':
            return (timing, iterations)
        else:
            return callback(timing, iterations)


    def repeat(self, trials, *, iterations=None, callback=None):
        """Call timeit() a few times.

        This is a convenience function that calls the timeit()
        repeatedly, returning a list of results.  The first argument
        specifies how many times to call timeit(), defaulting to 5;
        the second argument specifies the timer argument, defaulting
        to one million.

        Note: it's tempting to calculate mean and standard deviation
        from the result vector and report these.  However, this is not
        very useful.  In a typical case, the lowest value gives a
        lower bound for how fast your machine can run the given code
        snippet; higher values in the result vector are typically not
        caused by variability in Python's speed, but by other
        processes interfering with your timing accuracy.  So the min()
        of the result is probably the only number you should be
        interested in.  After that, you should look at the entire
        vector and apply common sense rather than statistics.
        """
        if isinstance(trials, int):
            if iterations is None:
                raise ValueError('iterations must be given with integer trials')
            if not isinstance(iterations, int):
                raise TypeError('iteration count must be integer')
            trials = itertools.repeat(iterations, trials)
        return list(
            feedback(trials, lambda t: self.timeit(t, callback=callback))
        )


def autorange(min_time):
    i = 1
    while True:
        for j in 1, 2, 5:
            number = i * j
            total_time, count = yield number
            assert count == number
            if total_time >= min_time:
                return
        i *= 10


def timeit(
    iterations, *,
    stmt="pass", setup="pass", timer=default_timer, globals=None,
    callback=None
):
    """Convenience function to create Timer object and call timeit method."""
    t = Timer(stmt, setup, timer, globals)
    return t.timeit(iterations, callback=callback)


def repeat(
    trials, *,
    stmt="pass", setup="pass", timer=default_timer, globals=None,
    iterations=None, callback=None
):
    """Convenience function to create Timer object and call repeat method."""
    t = Timer(stmt, setup, timer, globals)
    return t.repeat(trials, iterations=iterations, callback=callback)


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
        '-p', '--process', action='store_const', dest='timer',
        const=time.process_time, default=default_timer,
        help='use `time.process_time` for timing (default is `time.perf_counter`)'
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


def run(args):
    timer = Timer('\n'.join(args.stmt), '\n'.join(args.setup), args.timer)
    trials, iterations, unit = args.trials, args.iterations, args.unit
    precision = 3 if args.verbose == 0 else 2 + args.verbose
    func = run_verbose if args.verbose else run_plain
    return func(timer, trials, iterations, precision, unit)


def main(args=None, *, _wrap_timer=None):
    """Main program, used when run as a script.

    The optional 'args' argument specifies the command line to be parsed,
    defaulting to sys.argv[1:].

    The return value is an exit code to be passed to sys.exit(); it
    may be None to indicate success.

    When an exception happens during timing, a traceback is printed to
    stderr and the return value is 1.  Exceptions at other times
    (including the template compilation) are not caught.

    '_wrap_timer' is an internal interface used for unit testing.  If it
    is not None, it must be a callable that accepts a timer function
    and returns another timer function (used for unit testing).
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
    # Allow test code to replace the timer other than via the command line.
    if _wrap_timer is not None:
        args.timer = _wrap_timer(args.timer)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
