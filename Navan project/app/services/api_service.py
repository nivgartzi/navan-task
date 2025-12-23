import os
import httpx
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

class APIService:
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_KEY")

    async def search_hotels(self, city: str, check_in: str = None, check_out: str = None):
        """
        Searches for hotels in a city using SerpAPI (Google Hotels API).
        
        Args:
            city: The city name to search for hotels
            check_in: Check-in date (YYYY-MM-DD) - optional but recommended
            check_out: Check-out date (YYYY-MM-DD) - optional but recommended
        """
        print(f"🔍 Searching hotels in {city}...")
        if not self.serpapi_key:
            print("⚠️ SerpAPI key not found - using mock data")
            # Return mock data if API key is missing
            return self._get_mock_hotels(city)
        
        # Build SerpAPI request - dates are required by API, use defaults if not provided
        from datetime import datetime, timedelta
        today = datetime.now()
        
        # Default to tomorrow for check-in, day after for check-out if not provided
        if not check_in:
            check_in = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        if not check_out:
            check_out = (today + timedelta(days=2)).strftime("%Y-%m-%d")
        
        params = {
            "engine": "google_hotels",
            "q": f"hotels in {city}",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": "2",
            "currency": "USD",
            "gl": "us",
            "hl": "en",
            "api_key": self.serpapi_key
        }
        
        url = "https://serpapi.com/search"
        
        async with httpx.AsyncClient() as client:
            try:
                # Reduced timeout to 15 seconds, with faster fallback
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                
                # Parse SerpAPI Google Hotels response
                hotels = []
                
                # SerpAPI returns hotels in "properties" array
                if "properties" in data:
                    for prop in data["properties"][:5]:  # Limit to top 5
                        # Extract price from rate_per_night
                        price = None
                        if "rate_per_night" in prop:
                            price = prop["rate_per_night"].get("extracted_lowest")
                        if price is None and "total_rate" in prop:
                            price = prop["total_rate"].get("extracted_lowest")
                        
                        # Extract address from various possible fields
                        location = prop.get("location", {})
                        location_address = location.get("address") if isinstance(location, dict) else None
                        address = (
                            prop.get("address") or 
                            prop.get("full_address") or 
                            location_address or
                            prop.get("neighborhood") or 
                            prop.get("district") or
                            city  # Fallback to city name
                        )
                        
                        # Extract URL/link if available
                        link = prop.get("link") or prop.get("website") or prop.get("booking_link")
                        # If no link, construct Google Hotels search URL
                        if not link:
                            hotel_name = prop.get("name", "")
                            query = f"{hotel_name} {city}"
                            link = f"https://www.google.com/travel/hotels?q={urllib.parse.quote(query)}"
                        
                        hotel = {
                            "name": prop.get("name", "Unknown Hotel"),
                            "price": price if price else self._extract_price(prop),
                            "rating": prop.get("overall_rating", "N/A"),
                            "type": prop.get("type", "hotel").title(),
                            "address": address,
                            "reviews": prop.get("reviews", 0),
                            "link": link
                        }
                        hotels.append(hotel)
                
                # Also check "ads" array for sponsored results
                if "ads" in data and len(hotels) < 5:
                    for ad in data["ads"][:5-len(hotels)]:
                        # Extract URL/link if available
                        link = ad.get("link") or ad.get("website") or ad.get("booking_link")
                        # If no link, construct Google Hotels search URL
                        if not link:
                            hotel_name = ad.get("name", "")
                            query = f"{hotel_name} {city}"
                            link = f"https://www.google.com/travel/hotels?q={urllib.parse.quote(query)}"
                        
                        # Extract address from various possible fields for ads too
                        location = ad.get("location", {})
                        location_address = location.get("address") if isinstance(location, dict) else None
                        address = (
                            ad.get("address") or 
                            ad.get("full_address") or 
                            location_address or
                            ad.get("neighborhood") or 
                            ad.get("district") or
                            city  # Fallback to city name
                        )
                        
                        hotel = {
                            "name": ad.get("name", "Unknown Hotel"),
                            "price": ad.get("extracted_price"),
                            "rating": ad.get("overall_rating", "N/A"),
                            "type": "Hotel",
                            "address": address,
                            "reviews": ad.get("reviews", 0),
                            "link": link
                        }
                        if hotel["price"]:  # Only add if price exists
                            hotels.append(hotel)
                
                if hotels:
                    print(f"✓ Found {len(hotels)} hotels via SerpAPI")
                    return {
                        "hotels": hotels,
                        "source": "SerpAPI (Google Hotels)",
                        "city": city
                    }
                else:
                    # If no hotels found, return mock data
                    print(f"⚠️ No hotels found in SerpAPI response - using mock data")
                    print(f"   Response keys: {list(data.keys())}")
                    return self._get_mock_hotels(city)
                    
            except httpx.TimeoutException:
                print(f"SerpAPI timeout for {city} - using mock data")
                return self._get_mock_hotels(city)
            except httpx.HTTPStatusError as e:
                print(f"SerpAPI HTTP Error {e.response.status_code} for {city}: {e}")
                return self._get_mock_hotels(city)
            except Exception as e:
                print(f"SerpAPI Hotel Search Error for {city}: {e}")
                # Return mock data on error
                return self._get_mock_hotels(city)
    
    def _extract_price(self, hotel_data: dict) -> float:
        """Extracts price from various SerpAPI response formats."""
        # Try rate_per_night.extracted_lowest (most common)
        if "rate_per_night" in hotel_data:
            rpn = hotel_data["rate_per_night"]
            if isinstance(rpn, dict) and "extracted_lowest" in rpn:
                return float(rpn["extracted_lowest"])
        
        # Try total_rate.extracted_lowest
        if "total_rate" in hotel_data:
            tr = hotel_data["total_rate"]
            if isinstance(tr, dict) and "extracted_lowest" in tr:
                return float(tr["extracted_lowest"])
        
        # Try direct extracted_price (for ads)
        if "extracted_price" in hotel_data:
            return float(hotel_data["extracted_price"])
        
        # Try direct price field
        if "price" in hotel_data:
            price = hotel_data["price"]
            if isinstance(price, (int, float)):
                return float(price)
            if isinstance(price, str):
                # Remove currency symbols and parse
                price_clean = price.replace("$", "").replace(",", "").strip()
                try:
                    return float(price_clean)
                except ValueError:
                    pass
        
        # Default mock price based on hotel name
        seed = sum(ord(c) for c in hotel_data.get("name", "")) % 20
        return 150.0 + seed * 10
    
    def _get_mock_hotels(self, city: str) -> dict:
        """Returns mock hotel data when API is unavailable."""
        seed = sum(ord(c) for c in city) % 20
        price_base = 150 + seed * 10
        hotels_data = [
            {
                "name": f"The {city} Grand Royale",
                "price": price_base,
                "rating": "4.5",
                "type": "Luxury",
                "address": f"Downtown {city}",
                "reviews": 1200
            },
            {
                "name": f"{city} Business Boutique",
                "price": price_base - 70,
                "rating": "4.2",
                "type": "Business",
                "address": f"City Center, {city}",
                "reviews": 850
            },
            {
                "name": f"{city} Comfort Inn",
                "price": price_base - 100,
                "rating": "4.0",
                "type": "Mid-range",
                "address": f"Near Airport, {city}",
                "reviews": 650
            }
        ]
        
        # Add links to each hotel
        for hotel in hotels_data:
            query = f"{hotel['name']} {city}"
            hotel["link"] = f"https://www.google.com/travel/hotels?q={urllib.parse.quote(query)}"
        
        return {
            "hotels": hotels_data,
            "source": "Simulated (SerpAPI Key Missing)",
            "city": city
        }
