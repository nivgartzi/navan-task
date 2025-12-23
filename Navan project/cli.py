import asyncio
import os
from app.services.llm_engine import LLMEngine
from dotenv import load_dotenv

load_dotenv()

async def main():
    engine = LLMEngine()
    history = []
    
    print("========================================")
    print("   Booking Hotels Assistant")
    print("   Type 'exit' or 'quit' to stop.")
    print("========================================")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        print("\nThinking...", end="\r")
        response = await engine.chat(user_input, history)
        
        # Parse JSON response if needed
        import json
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict) and "response_to_user" in parsed:
                print(f"\nAssistant: {parsed['response_to_user']}")
                if parsed.get("thought_process"):
                    print(f"\n[Reasoning: {parsed['thought_process']}]")
                response_text = parsed['response_to_user']
            else:
                print(f"\nAssistant: {response}")
                response_text = response
        except json.JSONDecodeError:
            print(f"\nAssistant: {response}")
            response_text = response
        
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response_text})

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
