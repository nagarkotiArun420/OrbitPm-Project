from importlib.util import find_spec

from .development import *


if find_spec("config.settings.local_overrides"):
    from .local_overrides import *
