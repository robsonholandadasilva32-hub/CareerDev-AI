import os
import sys

# Ensure required env vars are set before importing modules that trigger Settings validation
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake")
os.environ.setdefault("GITHUB_CLIENT_ID", "fake")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "fake")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "fake")

import pytest
from app.services.social_harvester import SocialHarvester

def test_prepare_bytes_map():
    harvester = SocialHarvester()
    file_map = {"test.txt": ["React", "Python"]}
    bytes_map = harvester._prepare_bytes_map(file_map)

    assert "test.txt" in bytes_map
    # Check keys are bytes
    assert b"React" in bytes_map["test.txt"]
    assert b"Python" in bytes_map["test.txt"]
    # Check values are original strings
    assert bytes_map["test.txt"][b"React"] == "React"

def test_check_keywords_in_content_basic():
    harvester = SocialHarvester()
    content = b"This project uses React and Python."
    keyword_map = {b"react": "React", b"python": "Python", b"java": "Java"}

    found = harvester._check_keywords_in_content(content, keyword_map)

    assert "React" in found
    assert "Python" in found
    assert "Java" not in found

def test_check_keywords_in_content_case_insensitive():
    harvester = SocialHarvester()
    content = b"this project uses REACT and python."
    keyword_map = {b"react": "React", b"python": "Python"}

    found = harvester._check_keywords_in_content(content, keyword_map)

    assert "React" in found
    assert "Python" in found

def test_check_keywords_in_content_substring():
    harvester = SocialHarvester()
    # "reaction" contains "react"
    content = b"This is a reaction to the news."
    keyword_map = {b"react": "React", b"action": "Action"}

    found = harvester._check_keywords_in_content(content, keyword_map)

    assert "React" in found
    assert "Action" in found

def test_check_keywords_in_content_no_match():
    harvester = SocialHarvester()
    content = b"Nothing to see here."
    keyword_map = {b"react": "React"}

    found = harvester._check_keywords_in_content(content, keyword_map)
    assert len(found) == 0

def test_real_keywords_generation():
    harvester = SocialHarvester()
    # Check if real maps are populated
    assert "package.json" in harvester.scan_deps_map_bytes
    assert b"react" in harvester.scan_deps_map_bytes["package.json"]
    assert harvester.scan_deps_map_bytes["package.json"][b"react"] == "react"
