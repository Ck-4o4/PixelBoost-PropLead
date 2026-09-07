import os
import sys

# Set path
sys.path.insert(0, os.path.dirname(__file__))

# Import FastAPI application
from app import app

# Adapt ASGI (FastAPI) to WSGI for Passenger
try:
    from a2wsgi import ASGIMiddleware
    application = ASGIMiddleware(app)
except ImportError:
    # If a2wsgi is not installed, fallback
    application = app
