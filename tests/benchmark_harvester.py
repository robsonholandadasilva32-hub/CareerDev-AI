import os
import sys
import time
import tracemalloc
import random
import string

# Ensure required env vars are set before importing modules that trigger Settings validation
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake")
os.environ.setdefault("GITHUB_CLIENT_ID", "fake")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "fake")
os.environ.setdefault("AUTH_SECRET", "fake_secret")

from unittest.mock import MagicMock
sys.modules["tensorflow"] = MagicMock()
sys.modules["tensorflow.keras"] = MagicMock()
sys.modules["mlflow"] = MagicMock()

from app.services.social_harvester import SocialHarvester

def generate_random_content(size_mb, keywords):
    """Generates random bytes content of roughly size_mb, inserting keywords."""
    print(f"Generating {size_mb}MB of data...")
    size_bytes = size_mb * 1024 * 1024

    # Generate chunks of repeated text to simulate file content
    base_text = b"var x = function() { return 'nothing'; };\n" * 100
    repeats = size_bytes // len(base_text) + 1
    content = bytearray((base_text * repeats)[:size_bytes])

    # Insert keywords at random positions
    # We want to ensure we hit the search logic
    keyword_list = list(keywords)

    # 1. Insert at the beginning
    kw = keyword_list[0]
    content[0:len(kw)] = kw.upper().encode('utf-8')

    # 2. Insert at the end
    kw = keyword_list[1] if len(keyword_list) > 1 else keyword_list[0]
    content[-len(kw):] = kw.upper().encode('utf-8')

    # 3. Insert in the middle
    for kw in keyword_list[2:]:
        pos = random.randint(100, len(content) - 100)
        content[pos:pos+len(kw)] = kw.upper().encode('utf-8')

    return bytes(content)

def run_benchmark():
    harvester = SocialHarvester()

    # Use package.json keywords
    # Keys are bytes, values are strings
    keyword_map = harvester.scan_deps_map_bytes["package.json"]
    # We need the keys as strings for generation function
    keywords = [k.decode('utf-8') for k in keyword_map.keys()]

    # 20MB Content to make memory usage obvious
    # If lower() copies, we expect +20MB peak.
    content = generate_random_content(20, keywords)

    print(f"Content size: {len(content)/1024/1024:.2f} MB")

    # Warmup? No, we want cold start memory

    tracemalloc.start()
    start_time = time.perf_counter()

    found = harvester._check_keywords_in_content(content, keyword_map)

    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Peak memory allocation: {peak / 1024 / 1024:.2f} MB")
    print(f"Found keywords count: {len(found)}")

if __name__ == "__main__":
    run_benchmark()
