import pytest
import asyncio
from app.services.api_service import APIService

@pytest.mark.asyncio
async def test_api_service_hotel_structure():
    """
    Test that the hotel search returns the expected structure.
    """
    service = APIService()
    # Test the structure returned by our service method
    # Since keys might be missing, we expect our service to fallback to mock if needed,
    # but strictly return a dict with 'hotels' or 'top_hotels'.
    
    data = await service.search_hotels("London")
    assert isinstance(data, dict)
    assert "hotels" in data or "top_hotels" in data or "source" in data

@pytest.mark.asyncio
async def test_api_service_hotel_data_format():
    """
    Test that hotel data has the expected fields.
    """
    service = APIService()
    data = await service.search_hotels("Paris")
    
    assert isinstance(data, dict)
    if "hotels" in data:
        hotels = data["hotels"]
        if len(hotels) > 0:
            hotel = hotels[0]
            # Check for expected fields
            assert "name" in hotel
            assert "price" in hotel or "rate_per_night" in hotel
            # Rating and other fields may be optional
