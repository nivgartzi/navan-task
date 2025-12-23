from typing import Dict, Any, List, Tuple

class DataFusionValidator:
    """
    Validates that API data and LLM outputs are meaningfully and accurately blended.
    
    Ensures:
    1. API data is actually used (not ignored)
    2. LLM adds meaningful context (not just repeating API data)
    3. Blending is accurate (API facts preserved)
    4. Synthesis is meaningful (LLM provides value beyond raw data)
    """
    
    @staticmethod
    def validate_fusion_quality(api_data: Dict[str, Any], llm_response: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates that API data and LLM outputs are meaningfully blended.
        
        Returns:
            Tuple of (is_valid, issues_list)
        """
        issues = []
        is_valid = True
        
        # Extract components
        response_text = llm_response.get("response_to_user", "")
        llm_claims = llm_response.get("claims", {})
        api_hotels = api_data.get("top_hotels", [])
        llm_hotels = llm_claims.get("top_hotels", [])
        
        # Validation 1: API Data Usage Check
        if api_hotels and not llm_hotels:
            issues.append(
                "FUSION ISSUE: API returned hotel data but LLM did not include it in claims. "
                "LLM may have ignored API data."
            )
            is_valid = False
        
        # Validation 2: Meaningful Synthesis Check
        if api_hotels and llm_hotels:
            # Check if LLM just copied data without adding value
            api_hotel_names = {h.get("name", "").lower() for h in api_hotels}
            llm_hotel_names = {h.get("name", "").lower() for h in llm_hotels}
            
            # LLM should use API data
            if not api_hotel_names.intersection(llm_hotel_names):
                issues.append(
                    "FUSION ISSUE: LLM hotel names don't match API hotel names. "
                    "LLM may have ignored or replaced API data."
                )
                is_valid = False
            
            # Check if response text provides meaningful context
            if response_text:
                # Response should mention hotels from API
                mentions_api_hotels = any(
                    name.lower() in response_text.lower() 
                    for name in api_hotel_names 
                    if name
                )
                
                if not mentions_api_hotels and api_hotels:
                    issues.append(
                        "FUSION ISSUE: Response text doesn't mention any hotels from API data. "
                        "LLM may not be synthesizing API data meaningfully."
                    )
                    is_valid = False
                
                # Response should add value beyond just listing (comparison, recommendation, context)
                value_indicators = [
                    "recommend", "suggest", "compare", "better", "best", "value",
                    "excellent", "great", "good", "option", "choice", "consider"
                ]
                adds_value = any(indicator in response_text.lower() for indicator in value_indicators)
                
                if not adds_value and len(api_hotels) > 1:
                    issues.append(
                        "FUSION ISSUE: Response doesn't provide meaningful synthesis. "
                        "LLM should compare, recommend, or provide context, not just list hotels."
                    )
                    # This is a warning, not critical
                    if is_valid:
                        issues.append("(Warning: Could add more meaningful synthesis)")
        
        # Validation 3: Accuracy Preservation Check
        if api_hotels and llm_hotels:
            # Verify that LLM preserved API data accurately
            api_hotel_map = {h.get("name", "").lower(): h for h in api_hotels if h.get("name")}
            
            for llm_hotel in llm_hotels:
                llm_name = llm_hotel.get("name", "").lower()
                api_hotel = api_hotel_map.get(llm_name)
                
                if api_hotel:
                    # Check if key facts are preserved
                    llm_price = llm_hotel.get("price")
                    api_price = api_hotel.get("price")
                    
                    if llm_price is not None and api_price is not None:
                        try:
                            if abs(float(llm_price) - float(api_price)) > 1.0:
                                issues.append(
                                    f"FUSION ACCURACY ISSUE: Price modified during fusion. "
                                    f"'{llm_hotel.get('name')}': API=${api_price}, LLM=${llm_price}"
                                )
                                is_valid = False
                        except (ValueError, TypeError):
                            pass
        
        # Validation 4: Meaningful Blending Check
        if api_hotels and response_text:
            # Check if response meaningfully combines API facts with LLM reasoning
            # Should have both factual statements (from API) and reasoning (from LLM)
            
            # Factual indicators (from API)
            factual_indicators = ["$", "star", "rating", "night", "hotel"]
            has_facts = any(indicator in response_text.lower() for indicator in factual_indicators)
            
            # Reasoning indicators (from LLM)
            reasoning_indicators = [
                "because", "since", "if", "recommend", "suggest", "consider",
                "better", "best", "value", "excellent", "great"
            ]
            has_reasoning = any(indicator in response_text.lower() for indicator in reasoning_indicators)
            
            if not has_facts:
                issues.append(
                    "FUSION QUALITY: Response lacks factual data from API. "
                    "Should include prices, ratings, or other API facts."
                )
                is_valid = False
            
            if not has_reasoning and len(api_hotels) > 1:
                issues.append(
                    "FUSION QUALITY: Response lacks meaningful reasoning or recommendations. "
                    "LLM should provide context, comparisons, or suggestions based on API data."
                )
                # Warning, not critical
        
        return is_valid, issues
    
    @staticmethod
    def validate_meaningful_synthesis(api_data: Dict[str, Any], llm_response: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates that the synthesis is meaningful (not just data dump).
        
        Returns:
            Tuple of (is_meaningful, explanation)
        """
        response_text = llm_response.get("response_to_user", "")
        api_hotels = api_data.get("top_hotels", [])
        
        if not api_hotels:
            return True, "No API data to synthesize"
        
        # Check for meaningful synthesis indicators
        synthesis_quality_indicators = {
            "comparison": ["compare", "versus", "vs", "better", "best", "difference"],
            "recommendation": ["recommend", "suggest", "consider", "prefer", "choose"],
            "context": ["because", "since", "for", "if you", "depending on"],
            "value_assessment": ["value", "worth", "excellent", "great", "good", "affordable"]
        }
        
        found_indicators = []
        for category, indicators in synthesis_quality_indicators.items():
            if any(indicator in response_text.lower() for indicator in indicators):
                found_indicators.append(category)
        
        if len(found_indicators) >= 2:
            return True, f"Meaningful synthesis detected: {', '.join(found_indicators)}"
        elif len(found_indicators) == 1:
            return True, f"Basic synthesis detected: {found_indicators[0]}"
        else:
            return False, "Response lacks meaningful synthesis - appears to be just data listing"
    
    @staticmethod
    def get_fusion_quality_score(api_data: Dict[str, Any], llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides a quality score for the data fusion.
        
        Returns:
            Dictionary with quality metrics
        """
        is_valid, issues = DataFusionValidator.validate_fusion_quality(api_data, llm_response)
        is_meaningful, synthesis_explanation = DataFusionValidator.validate_meaningful_synthesis(
            api_data, llm_response
        )
        
        # Calculate score
        score = 100
        if not is_valid:
            score -= 30
        if not is_meaningful:
            score -= 20
        score -= len(issues) * 5
        score = max(0, score)
        
        return {
            "score": score,
            "is_valid": is_valid,
            "is_meaningful": is_meaningful,
            "synthesis_quality": synthesis_explanation,
            "issues": issues,
            "grade": "Excellent" if score >= 90 else "Good" if score >= 70 else "Needs Improvement"
        }

