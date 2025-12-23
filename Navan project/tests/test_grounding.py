import pytest
from app.services.hallucination_manager import HallucinationManager

def test_grounding_verification_hotel_price():
    """
    Test that the manager catches price discrepancies in hotel data.
    """
    # 1. Real API Data
    api_data = {
        "top_hotels": [
            {
                "name": "Grand Hotel Paris",
                "price": 150,
                "rating": 4.5,
                "reviews": 1200
            },
            {
                "name": "Luxury Suites",
                "price": 250,
                "rating": 4.8,
                "reviews": 850
            }
        ]
    }

    # 2. Hallucinated Claims (LLM says $200 instead of $150)
    hallucinated_claims = {
        "top_hotels": [
            {
                "name": "Grand Hotel Paris",
                "price": 200,  # Wrong price!
                "rating": 4.5,
                "reviews": 1200
            }
        ]
    }

    # 3. Verify
    discrepancies = HallucinationManager.verify_grounding(api_data, hallucinated_claims)
    
    # 4. Assert
    assert len(discrepancies) > 0
    assert "Price" in discrepancies[0] or "price" in discrepancies[0]
    print("\nSUCCESS: Detected hotel price hallucination.")

def test_grounding_verification_hotel_name():
    """
    Test that the manager catches invented hotel names.
    """
    api_data = {
        "top_hotels": [
            {
                "name": "Grand Hotel Paris",
                "price": 150,
                "rating": 4.5
            }
        ]
    }

    hallucinated_claims = {
        "top_hotels": [
            {
                "name": "Fake Hotel Name",  # Not in API!
                "price": 150,
                "rating": 4.5
            }
        ]
    }

    discrepancies = HallucinationManager.verify_grounding(api_data, hallucinated_claims)
    
    assert len(discrepancies) > 0
    assert "HALLUCINATED HOTEL" in discrepancies[0] or "not in API" in discrepancies[0]
    print("\nSUCCESS: Detected invented hotel name.")

def test_grounding_verification_hotel_rating():
    """
    Test that the manager catches rating discrepancies.
    """
    api_data = {
        "top_hotels": [
            {
                "name": "Grand Hotel Paris",
                "price": 150,
                "rating": 4.5
            }
        ]
    }

    hallucinated_claims = {
        "top_hotels": [
            {
                "name": "Grand Hotel Paris",
                "price": 150,
                "rating": 5.0  # Wrong rating!
            }
        ]
    }

    discrepancies = HallucinationManager.verify_grounding(api_data, hallucinated_claims)
    
    assert len(discrepancies) > 0
    assert "Rating" in discrepancies[0] or "rating" in discrepancies[0]
    print("\nSUCCESS: Detected hotel rating hallucination.")

if __name__ == "__main__":
    test_grounding_verification_hotel_price()
    test_grounding_verification_hotel_name()
    test_grounding_verification_hotel_rating()
