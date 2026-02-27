"""Configuration management"""

import os


def get_env(key, default=None):
    return os.getenv(key, default)
