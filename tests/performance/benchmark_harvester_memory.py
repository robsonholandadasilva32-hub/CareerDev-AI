import os
import sys
import time
import tracemalloc
import asyncio
import logging

# Setup environment to avoid import errors
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake")
os.environ.setdefault("GITHUB_CLIENT_ID", "fake")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "fake")

# Add root to path
sys.path.append(os.getcwd())

from app.services.social_harvester import SocialHarvester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_large_content(size_mb: int, keywords: list) -> bytes:
    """Generates a large bytes content with occasional keywords."""
    logger.info(f"Generating {size_mb}MB of random content...")
    chunk_size = 1024 * 1024 # 1MB
    base_chunk = b"x" * (chunk_size - 100)

    parts = []
    for i in range(size_mb):
        # Inject a keyword occasionally
        kw = keywords[i % len(keywords)].encode('utf-8')
        padding = b" " * (100 - len(kw))
        parts.append(base_chunk + kw + padding)

    return b"".join(parts)

def benchmark_full_load():
    harvester = SocialHarvester()
    # Use one of the existing maps
    filename = "package.json"
    keyword_map = harvester.scan_deps_map_bytes[filename]

    # 50 MB
    content_size = 50
    # Keywords that exist in the map
    test_keywords = ["react", "vue", "next"]

    # Measure creation of content (simulating download)
    start_mem = tracemalloc.get_traced_memory()[1]

    content = generate_large_content(content_size, test_keywords)

    logger.info("Running baseline: _check_keywords_in_content (Full Load)")

    t0 = time.time()
    found = harvester._check_keywords_in_content(content, keyword_map)
    duration = time.time() - t0

    current, peak = tracemalloc.get_traced_memory()

    logger.info(f"Baseline Results:")
    logger.info(f"  Time: {duration:.4f}s")
    logger.info(f"  Peak Memory: {peak / 1024 / 1024:.2f} MB")
    logger.info(f"  Found: {len(found)} keywords")

    # Cleanup
    del content
    del found

if __name__ == "__main__":
    tracemalloc.start()

    try:
        benchmark_full_load()
    finally:
        tracemalloc.stop()
