# Booking Hotels Assistant

An AI assistant that helps you find hotels by combining real-time hotel data with smart recommendations.

## How to Run

### Prerequisites

- Python 3.8 or higher
- API KEYS are already set for your convenience.                                             

### Setup

**Install dependencies:**
   ```bash
   pip install fastapi uvicorn openai httpx python-dotenv pytest
   ```

### Running the Application

**Web Interface (Recommended):**
```bash
python main.py
```
Then open your browser to: `http://localhost:8015`

**Command Line Interface:**
```bash
python cli.py
```

## Screenshots

The `screenshots/` folder contains demonstration sessions with the assistant, showing example interactions and use cases.

## Project Structure

```
.
├── app/
│   └── services/
│       ├── api_service.py              # SerpAPI integration
│       ├── llm_engine.py               # OpenAI integration
│       ├── hallucination_manager.py    # Hallucination detection
│       └── data_fusion_validator.py    # Data fusion validation
├── static/                             # Web UI files
├── tests/                              # Test files
├── main.py                             # Web server
└── cli.py                              # Command-line interface
```



### Description

The project uses **two external APIs**:

1. **OpenAI API** - Provides the AI language model (GPT-4o-mini) for understanding user questions and generating helpful responses
2. **SerpAPI (Google Hotels)** - Provides real-time hotel data including prices, ratings, availability, and reviews

These APIs work together: SerpAPI gives us real hotel data, and OpenAI helps explain and recommend hotels based on that data.


### Decision Logic

The system has clear rules for when to use external data vs LLM knowledge:

**Decision process:**
1. User mentions a city → Immediately fetch hotel data from API
2. User asks about prices → Use API data only (LLM can explain, but prices come from API)
3. User asks for recommendations → Get API data first, then LLM provides comparisons and suggestions
4. User asks general travel questions → Use LLM knowledge (no API needed)


**1. Hallucination Prevention:**
- **Structured output** - Forces the LLM to use a specific format
- **Tool-based data fetching** - LLM can't invent data it has to fetch from API
- **Strict prompts** - Clear instructions to never invent hotel names, prices, or ratings

**2. Hallucination Detection:**
- **Grounding checks** - Compares LLM claims against API data
- **Consistency checks** - Looks for duplicate entries, invalid data, logical errors
- **Plausibility checks** - Flags unrealistic prices or suspicious patterns
- **Pattern detection** - Catches overconfident claims without data support

**3. Self-Correction:**
- If the system detects a mistake, it automatically asks the LLM to fix it
- This happens before the user sees the response
- Multiple attempts are made until the response is accurate

**4. Graceful Handling:**
- If APIs fail, the system clearly labels data as "simulated" (not real)
- Error messages explain what went wrong
- The system never pretends fake data is real

**Key judgment calls:**
- **Accuracy over completeness** - Better to say "I don't have that data" than to guess
- **Multiple verification layers** - Prevention, detection, and correction work together
- **Transparency** - Users know when data is from API vs simulated
- **Automatic recovery** - System fixes mistakes without bothering the user

### Data Fusion

The system combines external API data with LLM knowledge in a smart way:

**How it works:**
- **API data** provides the facts: hotel names, prices, ratings, addresses
- **LLM** adds value: explanations, comparisons, recommendations, and context
- **Verification layer** checks that all facts match the API data exactly

**Methods included:**
1. **Grounding Verification** - Compares what the LLM says against API data to catch mistakes
2. **Data Fusion Validation** - Makes sure API data is actually used and LLM adds meaningful context (not just listing)
3. **Accuracy Preservation** - Ensures prices, names, and ratings match API data exactly
4. **Meaningful Synthesis** - Validates that responses include comparisons, recommendations, and helpful analysis




---






