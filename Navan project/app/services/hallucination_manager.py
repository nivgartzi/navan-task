from typing import Dict, Any, List, Tuple
import re

class HallucinationManager:
    """
    Comprehensive hallucination detection and management system.
    
    Implements multiple heuristics to detect potential hallucinations and misinformation:
    1. Grounding Verification: Compares LLM claims against API data
    2. Consistency Checks: Validates internal consistency of responses
    3. Plausibility Checks: Validates if claims are realistic
    4. Pattern Detection: Identifies common hallucination patterns
    5. Confidence Scoring: Assigns confidence levels to detected issues
    """
    
    @staticmethod
    def verify_grounding(api_data: Dict[str, Any], llm_claims: Dict[str, Any]) -> List[str]:
        """
        Primary grounding verification: Compares LLM claims against raw API data.
        
        IMPORTANT: Only flags CONTRADICTIONS as hallucinations, NOT missing data.
        If API doesn't have a field (like address, link, etc.), that's fine - not a hallucination.
        Only flag when API has data and LLM contradicts it (e.g., API says $100, LLM says $200).
        
        Heuristics:
        - Exact match verification (names, prices, ratings) - only when both exist
        - Fuzzy matching for slight variations
        - Count validation (number of hotels)
        - Contradiction detection (not missing data detection)
        
        Returns:
            List of discrepancy messages describing detected hallucinations
        """
        discrepancies = []
        
        # Verify Hotel Names and Prices
        llm_hotels = llm_claims.get("top_hotels", llm_claims.get("hotels", []))
        api_hotels = api_data.get("top_hotels", [])
        
        # Heuristic 1: Empty API Data Check
        if not api_hotels:
            if llm_hotels:
                discrepancies.append(
                    "CRITICAL: LLM claimed hotels but API returned no results. "
                    "This suggests the LLM invented hotel data."
                )
            return discrepancies
        
        # Heuristic 2: Count Validation
        if llm_hotels and len(llm_hotels) > len(api_hotels):
            discrepancies.append(
                f"COUNT MISMATCH: LLM claimed {len(llm_hotels)} hotels but API only returned {len(api_hotels)}. "
                f"LLM may have invented additional hotels."
            )
        
        if llm_hotels:
            # Create a mapping of API hotel names (normalized) for quick lookup
            api_hotel_map = {}
            for ah in api_hotels:
                name_key = ah.get("name", "").lower().strip()
                if name_key:
                    api_hotel_map[name_key] = ah
            
            for lh in llm_hotels:
                llm_name = lh.get("name", "").strip()
                
                # Heuristic 3: Missing Name Detection
                if not llm_name:
                    discrepancies.append(
                        "INVALID DATA: LLM claimed a hotel with no name. "
                        "This is a data integrity issue."
                    )
                    continue
                
                name_key = llm_name.lower()
                match = api_hotel_map.get(name_key)
                
                # Heuristic 4: Name Verification with Fuzzy Matching
                if not match:
                    # Fuzzy matching for slight variations (e.g., "The Grand Hotel" vs "Grand Hotel")
                    found_match = False
                    for api_name, api_hotel in api_hotel_map.items():
                        # Check if names are similar (one contains the other or vice versa)
                        if (name_key in api_name or api_name in name_key) and len(name_key) > 5:
                            match = api_hotel
                            found_match = True
                            break
                    
                    if not found_match:
                        available_names = [h.get("name") for h in api_hotels[:3]]
                        discrepancies.append(
                            f"HALLUCINATED HOTEL: LLM claimed hotel '{llm_name}' but it's not in API results. "
                            f"Available hotels: {', '.join(available_names)}. "
                            f"This is a clear hallucination - the hotel does not exist in the API data."
                        )
                        continue
                
                # Heuristic 5: Price Verification
                # Only flag as hallucination if both values exist AND they contradict each other
                # Missing data is NOT a hallucination - only contradictions are hallucinations
                llm_price = lh.get("price")
                api_price = match.get("price")
                
                if llm_price is not None and api_price is not None:
                    try:
                        llm_price_float = float(llm_price)
                        api_price_float = float(api_price)
                        # Allow small differences due to rounding (within $1)
                        price_diff = abs(llm_price_float - api_price_float)
                        if price_diff > 1.0:
                            discrepancies.append(
                                f"PRICE HALLUCINATION: Price mismatch for '{llm_name}': "
                                f"${llm_price} (LLM) vs ${api_price} (API). "
                                f"Difference: ${price_diff:.2f}. LLM may have invented or modified the price."
                            )
                    except (ValueError, TypeError):
                        # Only flag as error if both are present but invalid format
                        discrepancies.append(
                            f"INVALID PRICE FORMAT: For '{llm_name}': LLM={llm_price}, API={api_price}. "
                            f"This suggests data corruption or hallucination."
                        )
                # If price is missing from API or LLM, that's fine - not a hallucination
                
                # Heuristic 6: Rating Verification
                # Only flag as hallucination if both values exist AND they contradict each other
                # Missing data is NOT a hallucination - only contradictions are hallucinations
                llm_rating = lh.get("rating")
                api_rating = match.get("rating")
                
                if llm_rating and api_rating:
                    try:
                        # Normalize ratings (handle both string "4.5" and float 4.5)
                        llm_rating_str = str(llm_rating).replace("star", "").replace("stars", "").strip()
                        api_rating_str = str(api_rating).replace("star", "").replace("stars", "").strip()
                        
                        # Extract numeric rating
                        llm_rating_num = re.search(r'[\d.]+', llm_rating_str)
                        api_rating_num = re.search(r'[\d.]+', api_rating_str)
                        
                        if llm_rating_num and api_rating_num:
                            llm_rating_val = float(llm_rating_num.group())
                            api_rating_val = float(api_rating_num.group())
                            
                            # Allow 0.1 difference for rating rounding
                            rating_diff = abs(llm_rating_val - api_rating_val)
                            if rating_diff > 0.1:
                                discrepancies.append(
                                    f"RATING HALLUCINATION: Rating mismatch for '{llm_name}': "
                                    f"{llm_rating} (LLM) vs {api_rating} (API). "
                                    f"Difference: {rating_diff:.2f}. LLM may have invented the rating."
                                )
                    except (ValueError, AttributeError):
                        pass  # Skip rating verification if parsing fails
                # If rating is missing from API or LLM, that's fine - not a hallucination
        
        return discrepancies
    
    @staticmethod
    def detect_misinformation_patterns(response_text: str, api_data: Dict[str, Any]) -> List[str]:
        """
        Detects common misinformation patterns in LLM responses.
        
        Heuristics:
        - Overconfident claims without API support
        - Vague references to non-existent data
        - Contradictory statements
        - Unverifiable claims
        
        Returns:
            List of detected misinformation patterns
        """
        issues = []
        
        # Pattern 1: Overconfident claims
        overconfident_patterns = [
            r"definitely",
            r"certainly",
            r"guaranteed",
            r"always",
            r"never fails"
        ]
        if not api_data.get("top_hotels"):
            for pattern in overconfident_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    issues.append(
                        f"MISINFORMATION PATTERN: Overconfident language ('{pattern}') used "
                        f"without API data support. This may mislead users."
                    )
                    break
        
        # Pattern 2: Vague references to specific data
        vague_data_patterns = [
            r"the best hotel",
            r"top rated",
            r"most popular",
            r"highly recommended"
        ]
        if not api_data.get("top_hotels"):
            for pattern in vague_data_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    issues.append(
                        f"MISINFORMATION PATTERN: Vague claim ('{pattern}') without specific API data. "
                        f"LLM may be making unsubstantiated claims."
                    )
                    break
        
        # Pattern 3: Specific numbers without API support
        if not api_data.get("top_hotels"):
            # Check for specific prices mentioned in text
            price_mentions = re.findall(r'\$\d+', response_text)
            if price_mentions:
                issues.append(
                    f"MISINFORMATION PATTERN: Specific prices mentioned ({', '.join(price_mentions)}) "
                    f"but no API data available. These prices may be hallucinated."
                )
        
        return issues
    
    @staticmethod
    def check_consistency(llm_claims: Dict[str, Any]) -> List[str]:
        """
        Checks internal consistency of LLM claims.
        
        Heuristics:
        - Duplicate hotel entries
        - Inconsistent data types
        - Missing required fields
        - Logical inconsistencies
        
        Returns:
            List of consistency issues
        """
        issues = []
        hotels = llm_claims.get("top_hotels", llm_claims.get("hotels", []))
        
        # Check for duplicates
        hotel_names = [h.get("name", "").lower() for h in hotels if h.get("name")]
        duplicates = [name for name in hotel_names if hotel_names.count(name) > 1]
        if duplicates:
            issues.append(
                f"CONSISTENCY ISSUE: Duplicate hotel entries found: {set(duplicates)}. "
                f"This suggests data processing errors."
            )
        
        # Check for required fields
        for i, hotel in enumerate(hotels):
            if not hotel.get("name"):
                issues.append(
                    f"CONSISTENCY ISSUE: Hotel at index {i} missing required 'name' field."
                )
        
        # Check for logical inconsistencies
        for hotel in hotels:
            price = hotel.get("price")
            rating = hotel.get("rating")
            
            # Price should be positive
            if price is not None:
                try:
                    if float(price) < 0:
                        issues.append(
                            f"CONSISTENCY ISSUE: Hotel '{hotel.get('name')}' has negative price: ${price}. "
                            f"This is logically inconsistent."
                        )
                except (ValueError, TypeError):
                    pass
            
            # Rating should be between 0 and 5
            if rating:
                try:
                    rating_str = str(rating).replace("star", "").replace("stars", "").strip()
                    rating_num = re.search(r'[\d.]+', rating_str)
                    if rating_num:
                        rating_val = float(rating_num.group())
                        if rating_val < 0 or rating_val > 5:
                            issues.append(
                                f"CONSISTENCY ISSUE: Hotel '{hotel.get('name')}' has invalid rating: {rating}. "
                                f"Ratings should be between 0 and 5."
                            )
                except (ValueError, AttributeError):
                    pass
        
        return issues
    
    @staticmethod
    def check_plausibility(llm_claims: Dict[str, Any]) -> List[str]:
        """
        Checks if LLM claims are plausible (realistic values).
        
        Heuristics:
        - Unrealistic prices (too high or too low)
        - Suspicious patterns (all hotels same price)
        - Unrealistic ratings distribution
        
        Returns:
            List of plausibility concerns
        """
        concerns = []
        hotels = llm_claims.get("top_hotels", llm_claims.get("hotels", []))
        
        if not hotels:
            return concerns
        
        prices = []
        ratings = []
        
        for hotel in hotels:
            price = hotel.get("price")
            rating = hotel.get("rating")
            
            if price is not None:
                try:
                    prices.append(float(price))
                except (ValueError, TypeError):
                    pass
            
            if rating:
                try:
                    rating_str = str(rating).replace("star", "").replace("stars", "").strip()
                    rating_num = re.search(r'[\d.]+', rating_str)
                    if rating_num:
                        ratings.append(float(rating_num.group()))
                except (ValueError, AttributeError):
                    pass
        
        # Check for unrealistic prices
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            
            if min_price < 10:
                concerns.append(
                    f"PLAUSIBILITY CONCERN: Very low price detected (${min_price}). "
                    f"This may be unrealistic or a data error."
                )
            
            if max_price > 10000:
                concerns.append(
                    f"PLAUSIBILITY CONCERN: Very high price detected (${max_price}). "
                    f"This may be unrealistic or a data error."
                )
            
            # Check for suspicious uniformity (all same price)
            if len(set(prices)) == 1 and len(prices) > 2:
                concerns.append(
                    f"PLAUSIBILITY CONCERN: All hotels have the same price (${prices[0]}). "
                    f"This is suspicious and may indicate data fabrication."
                )
        
        # Check for unrealistic rating distribution
        if ratings:
            if all(r == ratings[0] for r in ratings) and len(ratings) > 2:
                concerns.append(
                    f"PLAUSIBILITY CONCERN: All hotels have the same rating ({ratings[0]}). "
                    f"This is suspicious and may indicate data fabrication."
                )
        
        return concerns
    
    @staticmethod
    def comprehensive_check(api_data: Dict[str, Any], llm_claims: Dict[str, Any], 
                           response_text: str = "") -> Tuple[List[str], Dict[str, Any]]:
        """
        Comprehensive hallucination check combining all detection methods.
        
        Returns:
            Tuple of (all_issues, detection_summary)
        """
        all_issues = []
        
        # 1. Grounding verification (primary check)
        grounding_issues = HallucinationManager.verify_grounding(api_data, llm_claims)
        all_issues.extend(grounding_issues)
        
        # 2. Consistency checks
        consistency_issues = HallucinationManager.check_consistency(llm_claims)
        all_issues.extend(consistency_issues)
        
        # 3. Plausibility checks
        plausibility_concerns = HallucinationManager.check_plausibility(llm_claims)
        all_issues.extend(plausibility_concerns)
        
        # 4. Misinformation pattern detection (if response text provided)
        misinformation_issues = []
        if response_text:
            misinformation_issues = HallucinationManager.detect_misinformation_patterns(
                response_text, api_data
            )
            all_issues.extend(misinformation_issues)
        
        # Create summary
        summary = {
            "total_issues": len(all_issues),
            "grounding_issues": len(grounding_issues),
            "consistency_issues": len(consistency_issues),
            "plausibility_concerns": len(plausibility_concerns),
            "misinformation_patterns": len(misinformation_issues),
            "has_critical_issues": len(grounding_issues) > 0,
            "confidence": "HIGH" if len(all_issues) == 0 else "LOW"
        }
        
        return all_issues, summary
