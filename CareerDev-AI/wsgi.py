import sys
import os

# Add the project directory to the sys.path
# Uses the directory of the current file (wsgi.py) as the root
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.append(project_home)

from app.main import app as application

# This 'application' object is what WSGI servers look for
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
