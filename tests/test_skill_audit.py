import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.social_harvester import SocialHarvester
from app.services.career_engine import CareerEngine

@pytest.mark.asyncio
async def test_social_harvester_deep_scan():
    harvester = SocialHarvester()

    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client

        # We need to carefully mock the sequence of calls
        # 1. User Info
        # 2. Repos List
        # 3. For Repo 1:
        #    a. Languages
        #    b. Contents (root)
        #    c. File Download (requirements.txt)
        #    d. Events (Commit Velocity)

        # Side effect needs to handle different URLs or just a sequence
        # Sequence is safer if we know the order, but async gather makes order indeterminate for repo tasks.
        # But we only have 1 repo mocked.

        mock_client.get.side_effect = [
            # 1. User Info
            MagicMock(status_code=200, json=lambda: {"login": "testuser"}),
            # 2. Repos
            MagicMock(status_code=200, json=lambda: [
                {"name": "repo1", "languages_url": "url_lang", "contents_url": "url_content/{+path}"}
            ]),
            # 3.a Languages
            MagicMock(status_code=200, json=lambda: {"Python": 10000}),
            # 3.b Contents
            MagicMock(status_code=200, json=lambda: [
                {"name": "requirements.txt", "download_url": "dl_url"}
            ]),
            # 3.c File Download
            MagicMock(status_code=200, text="fastapi\npydantic"),
            # 3.d Events
            MagicMock(status_code=200, json=lambda: [])
        ]

        langs, metrics = await harvester._harvest_github_raw("fake_token")

        assert "Python" in langs
        assert "fastapi" in metrics["detected_frameworks"]

def test_career_engine_alignment():
    engine = CareerEngine()

    # Case A: Imposter
    li_data = {"claimed_skills": ["React", "Python"]}
    gh_metrics = {
        "raw_languages": {"Python": 500}, # Low python
        "detected_frameworks": [] # No react
    }

    audit = engine.analyze_alignment(li_data, gh_metrics)

    react_audit = next(item for item in audit if item["skill"] == "React")
    assert react_audit["status"] == "Imposter Detected"
    assert react_audit["badge"] == "critical"

    python_audit = next(item for item in audit if item["skill"] == "Python")
    # Python < 1000 bytes -> Imposter
    assert python_audit["status"] == "Imposter Detected"

    # Case B: Hidden Gem
    li_data_2 = {"claimed_skills": []}
    gh_metrics_2 = {
        "raw_languages": {"Rust": 10000},
        "detected_frameworks": ["tokio"]
    }

    audit_2 = engine.analyze_alignment(li_data_2, gh_metrics_2)

    rust_audit = next(item for item in audit_2 if item["skill"] == "Rust")
    assert rust_audit["status"] == "Hidden Gem"

    tokio_audit = next(item for item in audit_2 if item["skill"] == "Tokio")
    assert tokio_audit["status"] == "Hidden Gem"

    # Case C: Verified
    li_data_3 = {"claimed_skills": ["Fastapi"]}
    gh_metrics_3 = {
        "raw_languages": {"Python": 5000},
        "detected_frameworks": ["fastapi"]
    }

    audit_3 = engine.analyze_alignment(li_data_3, gh_metrics_3)

    fastapi_audit = next(item for item in audit_3 if item["skill"] == "Fastapi")
    assert fastapi_audit["status"] == "Verified Expert"
