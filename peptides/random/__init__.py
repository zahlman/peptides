# Grab the pieces and set up delegation to the default instance.
from .core import *
from .extra import *


for name in (
    'bits', 'data', 'boolean', 'decimal', 'between',
    'sample', 'values', 'shuffle', 'shuffled'
):
    globals()[name] = getattr(Generator._default, name)
