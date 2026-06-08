import pytest
from pathlib import Path
from services.providers.grants_gov import GrantsGovProvider
from services.providers.nih import NIHProvider
from services.providers.nsf import NSFProvider
from core.models import RawFOA

FIXTURE_DIR = Path(__file__).parent / "fixtures"

def test_grants_gov_parser():
    html = (FIXTURE_DIR / "grants_gov.html").read_text()
    raw = RawFOA(url="https://www.grants.gov/oppId=123", agency="Grants.gov", raw_text=html)
    provider = GrantsGovProvider()
    result = provider.parse(raw)
    
    assert "Artificial Intelligence" in result["title"]
    assert "Department of Health" in result["agency"]
    assert result["open_date"] == "2024-03-15"
    assert result["close_date"] == "2024-12-12"

def test_nih_parser():
    html = (FIXTURE_DIR / "nih.html").read_text()
    raw = RawFOA(url="https://grants.nih.gov/rfa-24-001.html", agency="NIH", raw_text=html)
    provider = NIHProvider()
    result = provider.parse(raw)
    
    assert "Artificial Intelligence" in result["title"]
    assert result["open_date"] == "2024-06-07"
    assert result["close_date"] == "2027-06-07"

def test_nsf_parser():
    html = (FIXTURE_DIR / "nsf.html").read_text()
    raw = RawFOA(url="https://www.nsf.gov/pims_id=123", agency="NSF", raw_text=html)
    provider = NSFProvider()
    result = provider.parse(raw)
    
    assert "Advanced Distributed Systems" in result["title"]
    assert result["open_date"] == "2024-01-01"
    assert result["close_date"] == "2024-10-15"
