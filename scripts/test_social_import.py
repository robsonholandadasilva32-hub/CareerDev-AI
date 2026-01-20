import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

try:
    from app.routes import social
    print("Successfully imported app.routes.social")
except Exception as e:
    print(f"Failed to import app.routes.social: {e}")
    sys.exit(1)
