def feedback(original_generator, func):
    """A helper function for mapping a function onto results of a generator.
    The results are fed back to the generator with `.send`, if available."""
    original_generator = iter(original_generator)
    try:
        value = next(original_generator)
    except StopIteration:
        return
    get_next = getattr(
        original_generator, 'send', lambda result: next(original_generator)
    )
    while True:
        result = func(value)
        yield result
        try:
            value = get_next(result)
        except StopIteration:
            break



