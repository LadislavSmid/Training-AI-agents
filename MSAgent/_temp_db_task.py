
import asyncio
import sys
import os
from agent_framework import ChatAgent, ChatMessage
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

async def run_task():
    from MSAgent.mcp_mssql import get_all_mcp_tools, DatabaseConfig

    # Create model
    model = OpenAIChatClient(
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1/"),
        model_id=os.getenv("OPENAI_MODEL_ID", "qwen2.5:7b"),
    )

    # Database config
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

    mcp_tools = get_all_mcp_tools(db_config)

    # Create agent
    agent = ChatAgent(
        chat_client=model,
        instructions='''You are a database analyst specializing in MS SQL Server operations.
Execute the requested task and provide clear, concise results.
If the user writes in Czech, respond in Czech.''',
        tools=mcp_tools,
    )

    thread = agent.get_new_thread()

    # Execute task
    task = '''Find the latest record in table ErrorLog and analyze the error it contains. Provide an explanation of the error in Czech.'''
    messages = [ChatMessage(role="user", text=task)]
    result = await agent.run(messages, thread=thread)

    print("AGENT_RESULT_START")
    print(result.text)
    print("AGENT_RESULT_END")

asyncio.run(run_task())
