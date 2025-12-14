import asyncio
import sys
import os
from agent_framework import ChatAgent, ChatMessage
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add path to MCP server
mcp_server_path = os.path.join(os.path.dirname(__file__), '')
sys.path.insert(0, os.path.abspath(mcp_server_path))

try:
    from server import get_all_mcp_tools, DatabaseConfig
except ImportError:
    print(f"Error: Cannot import 'server' from path: {mcp_server_path}")
    print("Check if the server.py file exists in this folder.")
    sys.exit(1)


async def main():
    print("=== AI Agent for Error Analysis ===")
    print("Connecting to Ollama server...\n")

    # Create OpenAI client for Ollama (compatible with OpenAI API)
    model = OpenAIChatClient(
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1/"),
        model_id=os.getenv("OPENAI_MODEL_ID", "gpt-oss:latest"),
    )

    # Create database configuration from environment variables
    db_config = DatabaseConfig(
        server=os.getenv("DB_SERVER", "localhost"),
        port=os.getenv("DB_PORT", "1433"),
        database=os.getenv("DB_NAME"),
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        driver=os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        use_windows_auth=os.getenv("USE_WINDOWS_AUTH", "false").lower() == "true",
        trust_cert=os.getenv("TRUST_SERVER_CERTIFICATE", "true").lower() == "true",
        encrypt=os.getenv("DB_ENCRYPT", "no")
    )

    # Automatically load all MCP tools from server with configuration
    mcp_tools = get_all_mcp_tools(db_config)
    print(f"Loaded {len(mcp_tools)} MCP tools:")
    for tool in mcp_tools:
        tool_name = getattr(tool, 'name', 'unknown')
        tool_desc = getattr(tool, 'description', 'No description')
        print(f"  - {tool_name}: {tool_desc}")
    print()

    # Create AI agent with Microsoft Agent Framework
    agent = ChatAgent(
        chat_client=model,
        instructions="""You are a helpful AI assistant specializing in error and problem analysis.
You help developers solve technical problems, analyze error messages.
You have access to an MS SQL database where you can search logs and error records.
If a user writes to you in Czech and if possible, you reply in Czech.""",
        tools=mcp_tools,
    )

    # Create conversation thread to maintain history
    thread = agent.get_new_thread()
    
    print("Agent is ready! (type 'exit' to quit)\n")

    # Main loop for message processing
    while True:
        user_input = input("User: ")

        if not user_input.strip():
            continue

        if user_input.strip().lower() == "exit":
            print("Shutting down agent...")
            break

        print("Agent: ", end="", flush=True)

        try:
            # Create message and get response from AI agent
            messages = [ChatMessage(role="user", text=user_input)]
            result = await agent.run(messages, thread=thread)
            print(result.text)
            print()

        except Exception as ex:
            print(f"\n[ERROR] Failed to get response: {ex}")
            print("Check if Ollama server is running at http://localhost:11434")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    asyncio.run(main())
