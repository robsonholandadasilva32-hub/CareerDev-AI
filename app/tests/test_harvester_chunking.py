import pytest
import asyncio
from app.services.social_harvester import SocialHarvester

# Mock streaming generator
async def mock_stream(chunks):
    for chunk in chunks:
        yield chunk

@pytest.mark.asyncio
async def test_check_keywords_in_stream_basic():
    harvester = SocialHarvester()
    content_chunks = [b"This project uses ", b"React completely."]
    # "React" is in the second chunk

    keyword_map = harvester.scan_deps_map_bytes["package.json"]
    # Ensure 'react' is in the map for package.json

    # We need to call the new async method
    # Since it is not implemented yet, this test expects it to exist.
    found = await harvester._check_keywords_in_stream(mock_stream(content_chunks), keyword_map)

    assert "react" in found

@pytest.mark.asyncio
async def test_check_keywords_in_stream_boundary_split():
    harvester = SocialHarvester()
    # Split "react" as "re" + "act"
    content_chunks = [b"This project uses re", b"act and other tools."]

    keyword_map = harvester.scan_deps_map_bytes["package.json"]

    found = await harvester._check_keywords_in_stream(mock_stream(content_chunks), keyword_map)

    assert "react" in found

@pytest.mark.asyncio
async def test_check_keywords_in_stream_boundary_complex():
    harvester = SocialHarvester()
    # "typescript" is 10 chars.
    # Split "types" + "cript"
    content_chunks = [b"We use types", b"cript here."]

    keyword_map = harvester.scan_deps_map_bytes["package.json"]

    found = await harvester._check_keywords_in_stream(mock_stream(content_chunks), keyword_map)

    assert "typescript" in found

@pytest.mark.asyncio
async def test_check_keywords_in_stream_multiple_boundaries():
    harvester = SocialHarvester()
    # "react", "vue"
    # "rea" | "ct" ... "vu" | "e"
    content_chunks = [b"check out rea", b"ct and vu", b"ejs"]

    keyword_map = harvester.scan_deps_map_bytes["package.json"]

    found = await harvester._check_keywords_in_stream(mock_stream(content_chunks), keyword_map)

    assert "react" in found
    assert "vue" in found

@pytest.mark.asyncio
async def test_check_keywords_in_stream_small_chunks():
    harvester = SocialHarvester()
    # Chunks size 1
    content_chunks = [b"r", b"e", b"a", b"c", b"t"]

    keyword_map = harvester.scan_deps_map_bytes["package.json"]

    found = await harvester._check_keywords_in_stream(mock_stream(content_chunks), keyword_map)

    assert "react" in found

@pytest.mark.asyncio
async def test_check_keywords_in_stream_overlap_buffer_reset():
    harvester = SocialHarvester()
    # Ensure buffer doesn't falsely concatenate distantly separated parts?
    # Actually, the logic is: keep last N bytes.
    # If we have "rea" ... [lots of bytes] ... "ct", it shouldn't match.

    # 100 bytes of gap
    gap = b"x" * 100
    content_chunks = [b"rea", gap, b"ct"]

    keyword_map = harvester.scan_deps_map_bytes["package.json"]

    found = await harvester._check_keywords_in_stream(mock_stream(content_chunks), keyword_map)

    assert "react" not in found
