import asyncio
import time
import uuid
import httpx
from datetime import datetime, timedelta
from app.db.session import SessionLocal, engine
from app.db.models.user import User
from app.db.models.security import UserSession
from app.core.jwt import create_access_token
from app.main import app
from app.db.base import Base

def setup_test_data():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Create a unique user
        unique_id = str(uuid.uuid4())[:8]
        email = f"bench_{unique_id}@example.com"
        user = User(
            email=email,
            hashed_password="hashed_password",
            full_name="Benchmark User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create session
        session_id = str(uuid.uuid4())
        user_session = UserSession(
            id=session_id,
            user_id=user.id,
            user_agent="Benchmark Agent",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(user_session)
        db.commit()

        # Generate Token
        token = create_access_token(
            data={"sub": str(user.id), "sid": session_id}
        )
        return user.id, session_id, token
    finally:
        db.close()

def cleanup(user_id, session_id):
    db = SessionLocal()
    try:
        db.query(UserSession).filter(UserSession.id == session_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
    finally:
        db.close()

async def run_benchmark():
    try:
        user_id, session_id, token = setup_test_data()
        print(f"Setup Benchmark User: {user_id}, Session: {session_id}")

        cookies = {"access_token": token}

        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            # Warmup
            print("Warming up...")
            await client.get("/health", cookies=cookies)

            start_time = time.time()
            requests_count = 50

            print(f"Executing {requests_count} requests to /health...")
            for i in range(requests_count):
                resp = await client.get("/health", cookies=cookies)
                if resp.status_code != 200:
                    print(f"Warning: Request failed with {resp.status_code}")

            total_time = time.time() - start_time
            avg_latency = (total_time / requests_count) * 1000 # ms

            print(f"\n--- Results ---")
            print(f"Total Time: {total_time:.4f}s")
            print(f"Average Latency per Request: {avg_latency:.2f} ms")

    finally:
        if 'user_id' in locals():
            cleanup(user_id, session_id)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
