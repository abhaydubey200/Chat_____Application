from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance used by both main.py and individual route modules
limiter = Limiter(key_func=get_remote_address)
