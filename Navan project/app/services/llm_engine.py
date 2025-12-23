import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any
from app.services.api_service import APIService
from app.services.hallucination_manager import HallucinationManager
from app.services.data_fusion_validator import DataFusionValidator
from app.services.hallucination_manager import HallucinationManager

load_dotenv()

class LLMEngine:
    def __init__(self):
        # Get API key and strip whitespace
        api_key = os.getenv("OPEN_AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            api_key = api_key.strip()
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found! Please set OPENAI_API_KEY or OPEN_AI_API_KEY in your .env file. "
                "Get your key from: https://platform.openai.com/api-keys"
            )
        
        self.client = OpenAI(api_key=api_key)
        self.api_service = APIService()
        self.model = "gpt-4o-mini"

    async def chat(self, user_input: str, history: List[Dict[str, str]] = []):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Limit history to stay within token limits
        history = history[-10:]
        
        system_prompt = """
        You are a Booking Hotels Assistant, a helpful and professional hotel booking assistant specializing in finding the perfect accommodations.
        
        CHAIN-OF-THOUGHT REASONING PROCESS:
        Before responding, you MUST follow this structured reasoning:
        1. **ANALYZE USER INTENT**: What is the user asking for? (Hotel search, price comparison, location preferences, amenities)
        2. **EXTRACT KEY INFORMATION**: What details do I have? (city, dates, budget, preferences, number of guests)
        3. **IDENTIFY MISSING DATA**: What information do I need to fetch from the API?
        4. **SELECT APPROPRIATE TOOL**: Call 'search_hotels' when a city is mentioned or hotel search is requested
        5. **SYNTHESIZE RESPONSE**: How do I combine API data with helpful hotel recommendations?
        6. **VERIFY ACCURACY**: Am I only stating facts from API responses? No invented hotel names, prices, or ratings.
        
        QUERY TYPE HANDLING (Support multiple hotel-related queries):
        - **Type 1: Hotel Search**: Search hotels in a city, compare options, suggest based on preferences
        - **Type 2: Price & Availability**: Check prices, availability, best deals
        - **Type 3: Recommendations**: Suggest hotels based on budget, location, amenities, or ratings
        
        CONVERSATION FLOW:
        1. **DESTINATION IDENTIFICATION**: When user mentions a city or location, confirm the destination
        2. **DATES & PREFERENCES**: Ask for check-in/check-out dates if not provided. TODAY IS {0}
        3. **HOTEL SEARCH**: Use 'search_hotels' tool to fetch real hotel data from Google Hotels API
        4. **RECOMMENDATIONS**: Present hotels with accurate information from API
        
        STRICT TRUTH RULE (Hallucination Prevention):
        - NEVER invent hotel names, prices, ratings, or addresses
        - ONLY state facts that are present in the API response data
        - If API data is missing, acknowledge uncertainty: "I don't have current data for that location, but..."
        - NEVER say "I found hotels" unless tool was called AND data exists in 'claims'
        - Prices must match exactly what the API returns
        - Hotel names must match exactly what the API returns
        
        CONTEXT MANAGEMENT:
        - Maintain conversation history and reference previous exchanges
        - Remember user preferences (budget, location, amenities mentioned)
        - Handle follow-up questions naturally (e.g., "What about cheaper options?", "Any hotels near the beach?")
        - Remember the city and dates from previous messages
        
        DATA FUSION STRATEGY (Critical for Meaningful & Accurate Blending):
        - **API Data (Source of Truth)**: Hotel names, prices, ratings, addresses, reviews MUST come from API
        - **LLM Knowledge (Context & Reasoning)**: Use LLM for explanations, comparisons, recommendations, travel advice
        - **Fusion Rule**: Combine API facts with LLM reasoning, but NEVER modify API data
        - **Meaningful Blending Required**: Don't just list hotels - provide rich comparisons, detailed recommendations, context, and value assessments
        - **Enhanced Reasoning Requirements (MANDATORY - Always Include)**:
          * ALWAYS provide thoughtful analysis - this is REQUIRED, not optional
          * ALWAYS compare hotels: "Comparing the options, X offers the best value at $Y/night with a Z rating, while Y is more expensive but has higher ratings"
          * ALWAYS explain trade-offs: "Hotel A is $50 cheaper but has 200 fewer reviews, making Hotel B's rating more reliable. However, Hotel A offers better value for budget-conscious travelers"
          * ALWAYS add contextual insights: "With 5000+ reviews, this 4.5-star rating is highly reliable. The $150/night price is excellent value for a hotel of this quality"
          * ALWAYS make recommendations: "For budget travelers, I recommend X because it offers solid quality at the lowest price. For those prioritizing ratings, Y is ideal with its exceptional 4.8-star rating and thousands of reviews"
          * ALWAYS provide actionable advice: "If price is your main concern, choose X. If you want the highest-rated option, choose Y. For the best balance, Z offers good quality at a reasonable price"
          * If you just list hotels without analysis, comparisons, and recommendations, you are FAILING to meet the requirements
          * Start your response with analysis/comparison, THEN list the hotels with details
        - **Example Good Fusion**: "I found several great options in Paris. Comparing them: The Grand Hotel at $150/night offers excellent value for a 4.5-star hotel - with over 2000 reviews, this rating is highly reliable. Hotel B at $200 has an exceptional 4.8 rating backed by 5000+ reviews, making it ideal for those prioritizing top-rated accommodations, though Grand Hotel offers better value. For budget-conscious travelers, Hotel C at $100 with a solid 4.2 rating provides good quality at an affordable price point.\n\n1. Grand Hotel\nPrice: $150/night\nRating: 4.5 (2000 reviews)\n\n2. Hotel B\nPrice: $200/night\nRating: 4.8 (5000 reviews)\n\n3. Hotel C\nPrice: $100/night\nRating: 4.2 (800 reviews)"
        - **Example Bad Fusion (Avoid)**: "Here are hotels: Grand Hotel $150, Hotel B $200, Hotel C $100." [Just listing, no analysis, comparisons, trade-offs, or recommendations]
        - **Synthesis Requirements**: 
          * Provide detailed comparisons when multiple options exist
          * Give specific, actionable recommendations with clear reasoning
          * Explain trade-offs and value propositions clearly
          * Add meaningful context about what makes each hotel a good choice
          * Help users make informed decisions with thoughtful analysis
        
        DECISION LOGIC (When to Use API vs LLM):
        **ALWAYS USE API DATA FOR:**
        - Hotel names, prices, ratings, addresses, review counts
        - Availability, check-in/check-out times
        - Amenities, hotel types, star ratings
        - Any factual, verifiable information about hotels
        
        **USE LLM KNOWLEDGE FOR:**
        - Explaining what ratings mean and their reliability (e.g., "4.5 stars with 5000+ reviews is highly reliable")
        - Comparing hotels with detailed analysis (price-to-value, rating reliability, review counts)
        - Providing thoughtful recommendations with clear reasoning ("Choose X if you value Y because...")
        - Explaining trade-offs between options ("X is cheaper but Y has better ratings")
        - Providing actionable advice based on different priorities (budget, quality, location)
        - Understanding user intent and clarifying questions
        - General travel information and context about neighborhoods/areas
        - Value assessments ("This hotel offers excellent value for its rating")
        - Helping users make informed decisions with comparative analysis
        
        **DECISION TREE:**
        1. IF user mentions city → CALL API (search_hotels)
        2. IF user asks about prices/availability → USE API DATA ONLY
        3. IF user asks for recommendations → CALL API FIRST, then LLM provides reasoning
        4. IF user asks general travel questions → USE LLM KNOWLEDGE (no API needed)
        5. IF API data exists → LLM can explain/compare, but CANNOT modify API data
        
        GENERAL RULES:
        - Always use the 'search_hotels' tool for REAL data from Google Hotels API (via SerpAPI)
        - Be proactive: If user mentions a city, immediately search for hotels there
        - Provide helpful, personalized recommendations based on user preferences
        - When hotels are found, provide a nicely formatted text response in 'response_to_user' with clean formatting
        - The UI also renders cards from the 'claims' object automatically, but users read the text too
        - CRITICAL: When user is thanking you, saying goodbye, or ending the conversation (e.g., "thank you", "thanks", "thank u", "bye", "goodbye"), DO NOT include any hotel data in the 'claims' object. Set 'top_hotels' to an empty array [] and do not include city or other hotel-related data. Just provide a friendly closing response without showing hotel cards again.
        - Be polite, professional, and helpful
        - Focus on helping users find the perfect hotel accommodation
        - Be empathetic and acknowledge user concerns or emotions before jumping to business questions
        - If user expresses worry, uncertainty, or concerns, address those first with reassurance, then proceed
        - Balance being helpful with being human - don't skip straight to dates if user has emotional concerns
        - CRITICAL: NEVER show API logs, raw API data, JSON responses, technical details, API response structures, or system information to users
        - NEVER quote or reference API response format, JSON structure, or tool responses when answering user questions
        - Always answer questions naturally in plain language: 
          * If asked "based on what did you have this availability" → Answer: "I searched for hotels using Google Hotels data for your dates"
          * If asked about data source → Say "I used Google Hotels search results" not "The API returned..." or show raw data
          * Keep all responses conversational and user-friendly, never technical or system-focused
        - DO NOT say "please hold on", "wait a moment", "I will search", "Let me search", or any waiting/process announcements - just search and provide results directly
        - DO NOT announce what you're going to do - just do it and show results immediately
        - Be direct and action-oriented: search, analyze, and present results without conversational process commentary
        - When listing hotels, ALWAYS include analysis: compare prices, explain value, discuss trade-offs, make recommendations
        
        RESPONSE FORMATTING FOR HOTEL LISTS (CRITICAL - STRICTLY ENFORCE):
        - ABSOLUTELY NO markdown formatting: NO asterisks (**), NO brackets ([]), NO links, NO URLs, NO markdown syntax
        - Hotel names: Write ONLY the plain name. "Hotel Soho Barcelona" - that's it. No asterisks, no brackets, no links
        - DO NOT include "Address" field in the text response at all
        - DO NOT include "[More info]" or "[More details]" or any similar text with links
        - DO NOT include any URLs or website links in the text response
        - Format hotels EXACTLY like this (ONLY these 3 lines per hotel):
          1. Hotel Name
          Price: $X/night
          Rating: X.X (X reviews)
          
          2. Next Hotel Name
          Price: $X/night
          Rating: X.X (X reviews)
        - Add a blank line between each hotel
        - ONLY include: Number, Hotel Name, Price, Rating. Nothing else.
        - CORRECT example: 
          "1. Hotel Soho Barcelona
          Price: $92/night
          Rating: 4.6 (1319 reviews)"
        - WRONG examples (NEVER INCLUDE THESE):
          "**[Hotel Name]**" (NO asterisks)
          "[More info](url)" (NO "More info" text)
          "[More details](url)" (NO "More details" text)
          "Address: Barcelona" (NO address field)
          Any URLs or links (NO links at all)
        
        Output format:
        You MUST return your response in valid JSON format:
        {{
            "thought_process": "Step-by-step reasoning: [1] Intent analysis, [2] Data extraction, [3] Tool selection, [4] Synthesis plan",
            "response_to_user": "Your helpful, accurate response based on API data",
            "claims": {{
                "city": "City Name (once confirmed)",
                "top_hotels": [
                    {{
                        "name": "Exact hotel name from API",
                        "price": 0,
                        "rating": "...",
                        "type": "...",
                        "address": "...",
                        "reviews": 0,
                        "link": "URL from API if available"
                    }}
                ]
            }}
        }}
        
        IMPORTANT: Only include hotel data in 'claims.top_hotels' when you are actively showing hotel recommendations. 
        If the user is thanking you, saying goodbye, or just having a casual conversation (not asking for hotels), 
        set 'top_hotels' to an empty array [] to prevent showing hotel cards unnecessarily.
        """.format(today)
        
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_input}]
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_hotels",
                    "description": "Searches for hotels in a city using Google Hotels API. Use this when user mentions a city or asks for hotel recommendations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "The city name to search for hotels (e.g., 'Paris', 'New York', 'Tokyo')"
                            },
                            "check_in": {
                                "type": "string",
                                "description": "Check-in date in YYYY-MM-DD format (optional)"
                            },
                            "check_out": {
                                "type": "string",
                                "description": "Check-out date in YYYY-MM-DD format (optional)"
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            response_format={"type": "json_object"}
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)
            full_api_data = {}
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    function_args = {}
                
                if function_name == "search_hotels":
                    api_data = await self.api_service.search_hotels(
                        function_args.get("city"),
                        function_args.get("check_in"),
                        function_args.get("check_out")
                    )
                else:
                    api_data = {"error": "Tool not found"}
                
                if isinstance(api_data, dict):
                    # Process hotel data
                    if "hotels" in api_data:
                        # Keep top 5 hotels
                        api_data = {
                            "top_hotels": api_data["hotels"][:5],
                            "city": api_data.get("city")
                        }
                        
                    full_api_data.update(api_data)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(api_data)
                })
            
            # Second call for final grounded response
            second_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            final_json_str = second_response.choices[0].message.content
            try:
                final_data = json.loads(final_json_str)
                llm_claims = final_data.get("claims", {})
                
                # COMPREHENSIVE HALLUCINATION DETECTION
                response_text = final_data.get("response_to_user", "")
                all_issues, detection_summary = HallucinationManager.comprehensive_check(
                    full_api_data, llm_claims, response_text
                )
                
                # DATA FUSION QUALITY VALIDATION
                fusion_is_valid, fusion_issues = DataFusionValidator.validate_fusion_quality(
                    full_api_data, final_data
                )
                fusion_quality_score = DataFusionValidator.get_fusion_quality_score(
                    full_api_data, final_data
                )
                
                if fusion_issues:
                    print(f"\n{'='*60}")
                    print(f"DATA FUSION QUALITY CHECK:")
                    print(f"  Score: {fusion_quality_score['score']}/100 ({fusion_quality_score['grade']})")
                    print(f"  Valid: {fusion_is_valid}")
                    print(f"  Meaningful: {fusion_quality_score['is_meaningful']}")
                    print(f"  Synthesis: {fusion_quality_score['synthesis_quality']}")
                    print(f"{'='*60}")
                    
                    for issue in fusion_issues:
                        print(f"  ⚠️  {issue}")
                    
                    # Add fusion issues to correction if critical
                    if not fusion_is_valid:
                        all_issues.extend(fusion_issues)
                
                if all_issues:
                    # Log detection summary
                    print(f"\n{'='*60}")
                    print(f"HALLUCINATION DETECTION SUMMARY:")
                    print(f"  Total Issues: {detection_summary['total_issues']}")
                    print(f"  Grounding Issues: {detection_summary['grounding_issues']}")
                    print(f"  Consistency Issues: {detection_summary['consistency_issues']}")
                    print(f"  Plausibility Concerns: {detection_summary['plausibility_concerns']}")
                    print(f"  Misinformation Patterns: {detection_summary['misinformation_patterns']}")
                    print(f"  Confidence: {detection_summary['confidence']}")
                    print(f"{'='*60}")
                    
                    for issue in all_issues:
                        print(f"  ⚠️  {issue}")
                    
                    # Self-Correction Loop
                    if detection_summary['has_critical_issues']:
                        correction_msg = (
                            f"CRITICAL SYSTEM ALERT: Your response contained {detection_summary['total_issues']} "
                            f"hallucination(s) compared to the API data:\n"
                            + "\n".join([f"- {issue}" for issue in all_issues[:5]])  # Limit to first 5
                            + "\n\nYou MUST correct your response immediately. Only use data that exists in the API response. "
                            f"Do not invent, modify, or guess any hotel names, prices, ratings, or other factual data."
                        )
                        messages.append({"role": "system", "content": correction_msg})
                        
                        correction_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            response_format={"type": "json_object"}
                        )
                        corrected_json = correction_response.choices[0].message.content
                        
                        # Verify correction
                        try:
                            corrected_data = json.loads(corrected_json)
                            corrected_claims = corrected_data.get("claims", {})
                            corrected_issues, _ = HallucinationManager.comprehensive_check(
                                full_api_data, corrected_claims, 
                                corrected_data.get("response_to_user", "")
                            )
                            
                            if corrected_issues:
                                print(f"⚠️  Correction still has {len(corrected_issues)} issues, but proceeding...")
                            else:
                                print("✓ Correction successful - all hallucinations resolved")
                            
                            return corrected_json
                        except json.JSONDecodeError:
                            return corrected_json
            
                return final_json_str
                
            except json.JSONDecodeError:
                return second_response.choices[0].message.content
        
        return response_message.content
