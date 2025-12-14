import asyncio
import sys
import os
from agent_framework import ChatAgent, ChatMessage
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


async def main():
    print("=== AI Translation Agent (English ↔ Czech) ===")
    print("Connecting to Ollama server...\n")

    # Create OpenAI client for Ollama with Czech translation model
    model = OpenAIChatClient(
        api_key="ollama",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/"),
        model_id="jobautomation/OpenEuroLLM-Czech",
    )

    # Create AI agent specialized for translation
    agent = ChatAgent(
        chat_client=model,
        instructions="""You are a professional translator specializing in English and Czech translations.

Your tasks:
- Translate text between English and Czech languages
- Automatically detect the source language
- Provide accurate and natural translations
- Preserve the meaning, tone, and style of the original text
- For technical terms, provide both translation and original term in brackets if needed

When user provides text:
1. Detect if it's English or Czech
2. Translate to the other language
3. Provide clear, natural translation

If the user asks in Czech, respond in Czech.
If the user asks in English, respond in English.""",
        tools=[],  # No additional tools needed for translation
    )

    # Create conversation thread to maintain history
    thread = agent.get_new_thread()

    print("Translation Agent is ready! (type 'exit' to quit)")
    print("Simply enter text in English or Czech to translate.\n")

    # Main loop for message processing
    while True:
        user_input = input("You: ")

        if not user_input.strip():
            continue

        if user_input.strip().lower() == "exit":
            print("Shutting down translation agent...")
            break

        print("Agent: ", end="", flush=True)

        try:
            # Create message and get response from AI agent
            messages = [ChatMessage(role="user", text=user_input)]
            result = await agent.run(messages, thread=thread)
            print(result.text)
            print()

        except Exception as ex:
            print(f"\n[ERROR] Failed to get translation: {ex}")
            print("Check if Ollama server is running at http://localhost:11434")
            print("and model 'jobautomation/OpenEuroLLM-Czech' is installed.")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    asyncio.run(main())
