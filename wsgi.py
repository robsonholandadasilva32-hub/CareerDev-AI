import sys
import os

# Add the project directory to the sys.path
path = os.path.expanduser('~/CareerDevAI') # Typical structure, adjustable
if path not in sys.path:
    sys.path.append(path)

from app.main import app as application

# This 'application' object is what WSGI servers look for
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
