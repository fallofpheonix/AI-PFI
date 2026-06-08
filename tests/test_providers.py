import pytest
import json
from pathlib import Path
from services.providers.grants_gov import GrantsGovProvider
from services.providers.nih import NIHProvider
from services.providers.nsf import NSFProvider
from core.models import RawFOA

FIXTURE_DIR = Path(__file__).parent / "fixtures"

def test_grants_gov_api_parser():
    data = (FIXTURE_DIR / "grants_gov.json").read_text()
    raw = RawFOA(url="https://www.grants.gov/oppId=123", agency="Grants.gov", raw_text=data)
    provider = GrantsGovProvider()
    result = provider.parse(raw)
    
    assert "Artificial Intelligence" in result["title"]
    assert "(API)" in result["title"]
    assert result["foa_id"] == "FOA-123456"
    assert result["open_date"] == "2024-03-15"
    assert result["close_date"] == "2024-12-12"

def test_nih_api_parser():
    data = (FIXTURE_DIR / "nih.json").read_text()
    raw = RawFOA(url="https://grants.nih.gov/rfa-AI-24-001.html", agency="NIH", raw_text=data)
    provider = NIHProvider()
    result = provider.parse(raw)
    
    assert "Artificial Intelligence" in result["title"]
    assert "(API)" in result["title"]
    assert result["foa_id"] == "RFA-AI-24-001"
    assert result["open_date"] == "2024-06-07"
    assert result["close_date"] == "2027-06-07"

def test_nsf_api_parser():
    data = (FIXTURE_DIR / "nsf.json").read_text()
    raw = RawFOA(url="https://www.nsf.gov/nsf23-615", agency="NSF", raw_text=data)
    provider = NSFProvider()
    result = provider.parse(raw)
    
    assert "Advanced Distributed Systems" in result["title"]
    assert "(API)" in result["title"]
    assert result["foa_id"] == "23-615"
    assert result["open_date"] == "2024-01-01"
    assert result["close_date"] == "2024-10-15"
    assert result["award_range"]["max"] == 1000000
