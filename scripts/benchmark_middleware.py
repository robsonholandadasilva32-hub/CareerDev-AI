import time
import os
import sys
import requests
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from jose import jwt
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import Base and ensure all models are registered via app.db.base
import app.db.base
from app.db.base import Base
from app.core.config import settings

# Configuration
DB_FILE = "benchmark.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"
BASE_URL = "http://127.0.0.1:8001"
NUM_REQUESTS = 200
CONCURRENCY = 20

# Setup DB
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Use raw SQL to avoid mapper configuration issues in this script
    with engine.connect() as conn:
        # Create User
        conn.execute(text("""
            INSERT INTO users (email, hashed_password, is_active, created_at)
            VALUES ('bench@example.com', 'hashed', 1, :now)
        """), {"now": datetime.utcnow()})

        # Get User ID (sqlite specific)
        user_id = conn.execute(text("SELECT id FROM users WHERE email='bench@example.com'")).scalar()

        # Create Session
        session_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO user_sessions (id, user_id, is_active, user_agent, last_active_at, created_at)
            VALUES (:sid, :uid, 1, 'Benchmark', :last_active, :now)
        """), {
            "sid": session_id,
            "uid": user_id,
            "last_active": datetime.utcnow(), # No update needed
            "now": datetime.utcnow()
        })
        conn.commit()

        return user_id, session_id

def generate_token(user_id, session_id):
    to_encode = {
        "sub": str(user_id),
        "sid": session_id,
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow()
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def run_server():
    import uvicorn
    # Set env var for the server process
    os.environ["DATABASE_URL"] = DATABASE_URL
    # We run uvicorn programmatically or via subprocess?
    # Subprocess is safer to avoid event loop conflicts in this script
    import subprocess

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--port", "8001",
        "--log-level", "error"
    ]

    proc = subprocess.Popen(
        cmd,
        env={**os.environ, "DATABASE_URL": DATABASE_URL}
    )
    return proc

def make_request(token):
    headers = {"Cookie": f"access_token={token}"}
    try:
        # We hit a non-existent endpoint to trigger middleware but skip controller logic
        # Expecting 404, but middleware runs first.
        resp = requests.get(f"{BASE_URL}/api/benchmark_404", headers=headers, timeout=5)
        return resp.status_code
    except Exception as e:
        return str(e)

def benchmark():
    print("Setting up DB...")
    user_id, session_id = setup_db()
    token = generate_token(user_id, session_id)

    print("Starting Server...")
    server_proc = run_server()

    # Wait for server to be ready
    print("Waiting for server to be ready...")
    for _ in range(30):
        try:
            requests.get(f"{BASE_URL}/health")
            print("Server is ready!")
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        print("Server failed to start within 30 seconds.")
        server_proc.kill()
        sys.exit(1)

    print(f"Starting Benchmark: {NUM_REQUESTS} requests, {CONCURRENCY} threads")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        results = list(executor.map(lambda _: make_request(token), range(NUM_REQUESTS)))

    end_time = time.time()
    total_time = end_time - start_time

    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except:
        server_proc.kill()

    # Cleanup
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    success_count = len([r for r in results if r == 404]) # 404 means it passed middleware
    print(f"Total Time: {total_time:.4f}s")
    print(f"RPS: {NUM_REQUESTS / total_time:.2f}")
    print(f"Success (404s): {success_count}/{NUM_REQUESTS}")

    if success_count < NUM_REQUESTS:
        print("Some requests failed or didn't reach 404 (check errors).")
        print("Sample errors:", set([r for r in results if r != 404][:5]))

if __name__ == "__main__":
    benchmark()
