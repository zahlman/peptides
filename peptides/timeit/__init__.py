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


import gc, itertools, linecache, os, time, traceback
from ..generator_feedback import feedback


__all__ = ["Timer", "autorange", "default_timer", "repeat", "timeit"]


dummy_src_name = "<timeit-src>"
default_timer = time.perf_counter


_globals = globals


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
    return src.replace("\n", "\n" + " "*indent)


class Timer:
    """Class for timing execution speed of small code snippets.

    stmt -> string or callable giving the code that will be timed.
    setup -> string or callable giving additional setup code.
    timer -> callable used for timing. Defaults to `time.perf_counter`.
    If a custom timer is desired, make sure it accepts zero arguments and
    returns a floating-point value.
    globals -> dict or None
    If specified, the code will be executed in that global namespace,
    instead of the `timeit` module's namespace.

    To measure the execution time of `stmt`, use the `timeit` method.
    The `repeat` method is a convenience to call timeit` multiple times and
    return a list of results.

    `stmt` and `setup` strings may contain newlines, as long as they don't
    contain multi-line string literals. If strings are used, they will be
    written directly into a compiled template; if callables are used, the
    template will call them (it will not try to embed their code).
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

        The advantage over the standard traceback is that source lines
        in the compiled template will be displayed.
        
        `file` -> file-like object to which the traceback will be written.
        This argument is forwarded to `traceback.print_exc`; the default
        is `sys.stderr`.

        Typical use:

            t = Timer(...)       # outside the try/except
            try:
                t.timeit(...)    # or t.repeat(...)
            except:
                t.print_exc()
        """
        if self.src is not None:
            linecache.cache[dummy_src_name] = (
                len(self.src), None, self.src.split("\n"), dummy_src_name
            )
        # else the source is already stored somewhere else
        traceback.print_exc(file=file)


    def timeit(self, iterations, *, callback=None):
        """Time several executions of the main statement.

        To be precise, this executes the setup statement once, and then
        executes the main statement multiple times in a loop, returning
        information about the amount of time taken.

        `iterations` -> int: the number of times to run the loop.
        `callback` -> None, 'raw' or a callable
        If None or not specified, `timeit` returns the average time per
        iteration. If a callable is given, it will be passed the total time
        and number of iterations, and its result is returned.
        For convenience, the string `'raw'` can also be used, in which case
        the total time and number of iterations are returned as a 2-tuple
        (equivalent to passing `tuple`).
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
        """Call timeit() multiple times and return a list of results.

        `trials` -> int or iterable
        If integer, specifies the number of times to call `timeit`.
        If an iterable, `timeit` will run once for each value, and those
        values will specify the number of iterations for each trial.
        In particular, if a generator is used, the results from each call
        of `timeit` will be fed back to the generator (with `.send`) so
        that it can respond to interim results.

        Example of `trials` as a generator:

            def run_twice():
                # Note that if e.g. we use `callback='raw'`, the
                # assigned value may have a different type and structure.
                time_taken = yield 1
                if time_taken > 0.001:
                    print("A single run takes over a millisecond; aborting.")
                else:
                    yield 1000

            my_timer.repeat(run_twice())

        `iterations` -> int
        If `trials` is an integer, gives the number of iterations to use
        for each trial. Otherwise, this parameter is ignored.

        `callback` -> as per `timeit`.

        Note: it's tempting to calculate and report the mean and standard
        deviation of the results in the returned list. However, this is not
        very useful. In a typical case, the lowest value gives a lower bound
        for how fast your machine can run the given code snippet; higher
        values in the result vector are typically not caused by variability
        in Python's speed, but by other processes interfering with your
        timing accuracy. So the min() of the result is probably the only
        number you should be interested in. After that, you should look at
        the entire list and apply common sense rather than statistics.
        """
        if isinstance(trials, int):
            if iterations is None:
                raise ValueError(
                    '`iterations` must be given when `trials` is an integer'
                )
            if not isinstance(iterations, int):
                raise TypeError('`iterations` must be integer')
            trials = itertools.repeat(iterations, trials)
        return list(
            feedback(trials, lambda t: self.timeit(t, callback=callback))
        )


def autorange(min_time):
    """A generator that produces iteration counts for `repeat`.

    Yields values from the sequence 1, 2, 5, 10, 20, 50, 100, ...
    until the time taken by a trial exceeds `min_time`.
    """
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
