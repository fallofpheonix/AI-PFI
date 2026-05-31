import pytest
from fastapi.testclient import TestClient
from api.service import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "AI-PFI Engine"}

def test_process_invalid_url():
    response = client.post("/process", json={"url": "not-a-url"})
    assert response.status_code == 422  # Validation error from Pydantic

@pytest.mark.asyncio
async def test_process_url_mock(mocker):
    # Mock the pipeline service to avoid actual network calls
    mock_record = mocker.Mock()
    mock_record.foa_id = "test-123"
    mock_record.title = "Test FOA"
    mock_record.agency = "Test Agency"
    mock_record.open_date = "2024-01-01"
    mock_record.close_date = "2024-12-31"
    mock_record.tags = {"research_domains": ["AI"]}
    mock_record.source_url = "http://example.com"
    mock_record.to_dict.return_value = {
        "foa_id": "test-123",
        "title": "Test FOA",
        "agency": "Test Agency",
        "open_date": "2024-01-01",
        "close_date": "2024-12-31",
        "tags": {"research_domains": ["AI"]},
        "source_url": "http://example.com"
    }

    # Use mocker to patch the pipeline in api.service
    mocker.patch("api.service.pipeline.process_url", return_value=mock_record)

    response = client.post("/process", json={"url": "http://example.com"})
    assert response.status_code == 200
    assert response.json()["foa_id"] == "test-123"
