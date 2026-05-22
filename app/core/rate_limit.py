from slowapi import Limiter
from slowapi.util import get_remote_address


# Default global limit can be overridden per-endpoint with @limiter.limit(...)
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
