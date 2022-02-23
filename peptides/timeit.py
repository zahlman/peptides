#! /usr/bin/python3.8

"""Tool for measuring execution time of small code snippets.

This module attempts to minimize overhead associated with the timing loop,
and avoid common traps in interpreting the results. The overhead is still
non-zero, and the code here doesn't try to hide that when reporting results.
To measure the timing overhead, try invoking the program without arguments.

Library usage: see the Timer class.

Command line usage:
    python timeit.py [-n N] [-r N] [-s S] [-p] [-h] [--] [statement]

Options:
  -n/--number N: how many times to execute 'statement' (default: see below)
  -r/--repeat N: how many times to repeat the timer (default 5)
  -s/--setup S: statement to be executed once initially (default 'pass').
                Execution of this setup statement is NOT timed.
  -p/--process: use time.process_time() (default is time.perf_counter())
  -v/--verbose: print raw timing results; repeat for more digits precision
  -u/--unit: set the output time unit (nsec, usec, msec, or sec)
  -h/--help: print this usage message and exit
  --: separate options from statement, use when statement starts with -
  statement: statement to be timed (default 'pass')

A multi-line statement may be given by specifying each line as a separate
argument; indented lines are possible by enclosing an argument in quotes and
using leading spaces. Multiple -s options are treated similarly.

If -n is not given, a suitable number of loops is calculated by trying
increasing numbers from the sequence 1, 2, 5, 10, 20, 50, ... until the
total time is at least 0.2 seconds.

Classes:

    Timer

Functions:

    timeit(string, string) -> float
    repeat(string, string) -> list
    default_timer() -> float
"""


import gc, getopt, itertools, linecache, os, sys, time, traceback, warnings
from functools import partial


__all__ = ["Timer", "timeit", "repeat", "default_timer"]


dummy_src_name = "<timeit-src>"
default_iterations = 1000000
default_trials = 5
default_timer = time.perf_counter


_globals = globals
_units = ((1.0, 'sec'), (1e-3, 'msec'), (1e-6, 'usec'), (1e-9, "nsec"))
_unit_names = tuple(u[1] for u in _units)


# Don't change the indentation of the template; the reindent() calls
# in Timer.__init__() depend on setup being indented 4 spaces and stmt
# being indented 8 spaces.
template = """
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


    def timeit(self, iterations=default_iterations, *, raw=False):
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
        return (timing, iterations) if raw else timing / iterations


    def repeat(
        self, trials=default_trials, *,
        raw=False, iterations=default_iterations
    ):
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
            trials = itertools.repeat(iterations, trials)
        return [self.timeit(trial, raw=raw) for trial in trials]


    def autorange(self, callback=None):
        """Return the number of loops and time taken so that total time >= 0.2.

        Calls the timeit method with increasing numbers from the sequence
        1, 2, 5, 10, 20, 50, ... until the time taken is at least 0.2
        second.  Returns (number, time_taken).

        If *callback* is given and is not None, it will be called after
        each trial with two arguments: ``callback(number, time_taken)``.
        """
        i = 1
        while True:
            for j in 1, 2, 5:
                number = i * j
                total_time, count = self.timeit(iterations=number, raw=True)
                assert count == number
                if callback:
                    callback(number, total_time)
                if total_time >= 0.2:
                    return (number, total_time)
            i *= 10


def timeit(
    stmt="pass", setup="pass", timer=default_timer, globals=None,
    *, iterations=default_iterations, raw=False
):
    """Convenience function to create Timer object and call timeit method."""
    t = Timer(stmt, setup, timer, globals)
    return t.timeit(iterations=iterations, raw=raw)


def repeat(
    stmt="pass", setup="pass", timer=default_timer, globals=None,
    trials=default_trials, *, iterations=default_iterations, raw=False
):
    """Convenience function to create Timer object and call repeat method."""
    t = Timer(stmt, setup, timer, globals)
    return t.repeat(trials, iterations=iterations, raw=raw)


def _bailout(*messages):
    print(*messages, sep='\n', file=sys.stderr)
    return 2


def _parse_args(args):
    if args is None:
        args = sys.argv[1:]
    try:
        opts, args = getopt.getopt(
            args, "n:u:s:r:pvh", [
                "number=", "unit=", "setup=", "repeat=",
                "process", "verbose", "help"
            ]
        )
    except getopt.error as err:
        return _bailout(err, "use -h/--help for command line help")
    # Process individual arguments.
    timer = default_timer
    number = 0 # auto-determine
    setup = []
    repeat = default_trials
    verbose = 0
    unit_name = None
    precision = 3
    for o, a in opts:
        if o in ("-n", "--number"):
            number = int(a)
        if o in ("-s", "--setup"):
            setup.append(a)
        if o in ("-u", "--unit"):
            if a in _unit_names:
                unit_name = a
            else:
                return _bailout(
                    "Unrecognized unit. Please select nsec, usec, msec, or sec.",
                )
        if o in ("-r", "--repeat"):
            repeat = max(int(a), 1)
        if o in ("-p", "--process"):
            timer = time.process_time
        if o in ("-v", "--verbose"):
            if verbose:
                precision += 1
            verbose += 1
        if o in ("-h", "--help"):
            print(__doc__, end='')
            return 0
    return {
        'stmt': '\n'.join(args) if args else 'pass',
        'setup': '\n'.join(setup) if setup else 'pass',
        'timer': timer, 'number': number, 'repeat': repeat,
        'verbose': verbose, 'precision': precision, 'unit_name': unit_name
    }


def _autorange_callback(precision, number, time_taken):
    msg = "{num} loop{s} -> {secs:.{prec}g} secs"
    plural = (number != 1)
    print(msg.format(num=number, s='s' if plural else '',
                      secs=time_taken, prec=precision))


def _auto_number(t, verbose, precision):
    callback = partial(_autorange_callback, precision) if verbose else None
    result, _ = t.autorange(callback)
    if verbose:
        print()
    return result


def format_time(precision, desired_name, dt):
    for scale, name in _units:
        if name == desired_name or (desired_name is None and dt >= scale):
            return f"{dt/scale:.{precision}g} {name}"
    else:
        assert False


def print_stats(number, repeat, raw_timings, verbose, precision, unit_name):
    if verbose:
        print("raw times:", ", ".join(
            format_time(precision, unit_name, dt[0]) for dt in raw_timings
        ), end='\n\n')
    timings = [dt / count for dt, count in raw_timings]
    best, worst = min(timings), max(timings)
    formatted_best = format_time(precision, unit_name, best)
    formatted_worst = format_time(precision, unit_name, worst)
    s = '' if number == 1 else 's'
    print(f"{number} loop{s}, best of {repeat}: {formatted_best} per loop")
    if worst >= best * 4:
        msg_1 = "The test results are likely unreliable. The worst time"
        msg_2 = "was more than four times slower than the best time"
        warnings.warn_explicit(
            f"{msg_1} ({formatted_worst}) {msg_2} ({formatted_best}).",
            UserWarning, '', 0
        )


def run(stmt, setup, timer, number, repeat, verbose, precision, unit_name):
    t = Timer(stmt, setup, timer)
    try:
        if number == 0:
            number = _auto_number(t, verbose, precision)
        raw_timings = t.repeat(repeat, iterations=number, raw=True)
    except:
        t.print_exc()
        return 1
    print_stats(number, repeat, raw_timings, verbose, precision, unit_name)
    return 0


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
    args = _parse_args(args)
    if isinstance(args, int):
        return args
    # Include the current directory, so that local imports work (sys.path
    # contains the directory of this script, rather than the current
    # directory)
    sys.path.insert(0, os.curdir)
    # Allow test code to replace the timer other than via the command line.
    if _wrap_timer is not None:
        args['timer'] = _wrap_timer(args['timer'])
    return run(**args)


if __name__ == "__main__":
    sys.exit(main())
