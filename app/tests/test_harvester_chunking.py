import os
import sys

# Ensure required env vars are set before importing modules that trigger Settings validation
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake")
os.environ.setdefault("GITHUB_CLIENT_ID", "fake")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "fake")
os.environ.setdefault("AUTH_SECRET", "fake_secret")

import pytest
from app.services.social_harvester import SocialHarvester

def test_chunking_overlap_detection():
    harvester = SocialHarvester()

    # We want to force a split across chunk boundary.
    # Chunk size is 65536.
    # We'll create content where "keyword" spans 65535 and 65536.

    # keyword "TARGET" (6 chars)
    # boundary is at 65536.
    # We place "TAR" at 65533-65535 and "GET" at 65536-65538.

    chunk_size = 65536
    keyword = "TARGET"

    # Prefix length = chunk_size - 3
    prefix = b"a" * (chunk_size - 3)
    # Content = prefix + TARGET + suffix
    content = prefix + b"TARGET" + b"b" * 100

    # Verify position:
    # "TARGET" is at index 65533.
    # content[65533:65539] is b"TARGET".
    # Chunk 1: content[0:65536]. Ends with "TAR".
    # Chunk 2 (starts at 65536 - overlap).
    # Overlap = len(keyword) - 1 = 5.
    # Chunk 2 starts at 65531.
    # Chunk 2 should contain "TARGET".

    keyword_map = {b"target": "TARGET"}

    found = harvester._check_keywords_in_content(content, keyword_map)
    assert "TARGET" in found

def test_chunking_exact_boundary():
    harvester = SocialHarvester()
    # Keyword exactly at the start of second chunk (without overlap it would be fine, but overlap shouldn't break it)
    chunk_size = 65536
    prefix = b"a" * chunk_size
    content = prefix + b"TARGET"

    keyword_map = {b"target": "TARGET"}
    found = harvester._check_keywords_in_content(content, keyword_map)
    assert "TARGET" in found

def test_multiple_keywords_across_chunks():
    harvester = SocialHarvester()
    # K1 at start
    # K2 spanning boundary
    # K3 at end
    chunk_size = 65536
    k1 = "FIRST"
    k2 = "MIDDLE"
    k3 = "LAST"

    content = bytearray(chunk_size * 2 + 100)
    # Fill with garbage
    content[:] = b'x' * len(content)

    # Place K1
    content[0:5] = b"FIRST"
    # Place K2 at split point
    pos_k2 = chunk_size - 3
    content[pos_k2:pos_k2+6] = b"MIDDLE"
    # Place K3
    content[-4:] = b"LAST"

    keyword_map = {b"first": "FIRST", b"middle": "MIDDLE", b"last": "LAST"}

    found = harvester._check_keywords_in_content(bytes(content), keyword_map)
    assert "FIRST" in found
    assert "MIDDLE" in found
    assert "LAST" in found
    assert len(found) == 3
