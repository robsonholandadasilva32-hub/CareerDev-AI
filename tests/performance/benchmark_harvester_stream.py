import os
import sys
import time
import tracemalloc
import asyncio
import logging

# Setup environment
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake")
os.environ.setdefault("GITHUB_CLIENT_ID", "fake")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "fake")
os.environ.setdefault("AUTH_SECRET", "fake")

sys.path.append(os.getcwd())

from app.services.social_harvester import SocialHarvester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_stream(size_mb: int, keywords: list):
    """Generates a large content in chunks."""
    logger.info(f"Generating stream of {size_mb}MB...")
    chunk_size = 64 * 1024 # 64KB chunks (typical http chunk)

    total_bytes = size_mb * 1024 * 1024
    generated = 0

    base_chunk = b"x" * (chunk_size - 100)

    while generated < total_bytes:
        # Inject keyword occasionally
        kw = keywords[generated % len(keywords)].encode('utf-8')
        padding = b" " * (100 - len(kw))
        chunk = base_chunk + kw + padding

        yield chunk
        generated += len(chunk)

async def benchmark_stream():
    harvester = SocialHarvester()
    filename = "package.json"
    keyword_map = harvester.scan_deps_map_bytes[filename]

    content_size = 50
    test_keywords = ["react", "vue", "next"]

    logger.info("Running optimization: _check_keywords_in_stream (Streaming)")

    start_mem = tracemalloc.get_traced_memory()[1]

    t0 = time.time()

    # We measure memory *during* the process
    # But tracemalloc tracks peak since start.
    tracemalloc.reset_peak()

    stream = generate_stream(content_size, test_keywords)
    found = await harvester._check_keywords_in_stream(stream, keyword_map)

    duration = time.time() - t0

    current, peak = tracemalloc.get_traced_memory()

    logger.info(f"Stream Results:")
    logger.info(f"  Time: {duration:.4f}s")
    logger.info(f"  Peak Memory: {peak / 1024 / 1024:.2f} MB")
    logger.info(f"  Found: {len(found)} keywords")

if __name__ == "__main__":
    tracemalloc.start()

    try:
        asyncio.run(benchmark_stream())
    finally:
        tracemalloc.stop()
