import asyncio
import time
import sys
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
from app.db.crud.users import create_user_async

# Setup In-Memory DB
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    print("Tables to create:", Base.metadata.tables.keys())
    Base.metadata.create_all(bind=engine)

async def benchmark():
    db = SessionLocal()
    try:
        start_time = time.time()
        iterations = 1000

        print(f"Starting benchmark with {iterations} iterations...")

        for i in range(iterations):
            unique_str = str(uuid.uuid4())
            await create_user_async(
                db=db,
                name=f"User {i}",
                email=f"user{unique_str}@example.com",
                hashed_password="hashed_secret",
                github_id=f"gh_{unique_str}"
            )

        end_time = time.time()
        duration = end_time - start_time
        print(f"Time taken: {duration:.4f} seconds")
        print(f"Average per user: {duration/iterations:.6f} seconds")
        return duration
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    asyncio.run(benchmark())
