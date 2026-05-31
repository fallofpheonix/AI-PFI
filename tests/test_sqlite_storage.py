
from pathlib import Path
from core.models.foa_record import FOARecord
from pipeline.storage.exporter import FOAStore
import pytest
import sqlite3

def test_sqlite_store_persistence(tmp_path):
    db_path = tmp_path / "test_foa.db"
    store = FOAStore(db_path)
    
    record = FOARecord(foa_id="TEST-001", title="Test Grant", source_name="test_agency")
    
    # Test insertion
    assert store.upsert(record) is True
    
    # Test containment
    assert store.contains("TEST-001") is True
    
    # Test rehydration
    records = store.all_records()
    assert len(records) == 1
    assert records[0].foa_id == "TEST-001"
    
    # Test update (should return False as it's the same)
    assert store.upsert(record) is False
    
    # Test update with change
    record.title = "Updated Title"
    assert store.upsert(record) is True
    
    updated_records = store.all_records()
    assert updated_records[0].title == "Updated Title"
