"""WSGI entrypoint for gunicorn on the droplet.

`app/__init__.py` already builds a module-level `app`, so this only re-exports
it under the name the systemd unit expects (`wsgi:app`), matching the other
Flask apps on the mdeller.com host.
"""

from app import app  # noqa: F401
