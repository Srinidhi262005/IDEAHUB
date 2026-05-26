import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Ideahub.wsgi import app

# Export the app for Vercel
handler = app
