import asyncio
import sys
import os
import subprocess
from typing import Optional
from agent_framework import ChatAgent, ChatMessage, ai_function
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add path to MCP server and other agents
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# Agent invocation functions - these actually run the specialized agents
@ai_function(
    name="query_database",
    description="Execute database query or analysis by invoking the specialized database analyst agent. Use for: querying tables, analyzing logs, investigating errors, finding records in database."
)
def query_database(task_description: str) -> dict:
    """
    Invoke database analyst agent to execute database operations.

    Args:
        task_description: Clear description of the database task (e.g., "Find last record in ErrorLog table and analyze the error")

    Returns:
        Dictionary with results from database agent
    """
    try:
        # Create a Python script that runs the agent with the task
        script = f"""
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
    from server import get_all_mcp_tools, DatabaseConfig

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
    task = '''{task_description}'''
    messages = [ChatMessage(role="user", text=task)]
    result = await agent.run(messages, thread=thread)

    print("AGENT_RESULT_START")
    print(result.text)
    print("AGENT_RESULT_END")

asyncio.run(run_task())
"""

        # Write temporary script
        temp_script = os.path.join(os.path.dirname(__file__), "_temp_db_task.py")
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(script)

        # Run the agent as subprocess
        process = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
            cwd=os.path.dirname(__file__)
        )

        # Clean up temp script
        try:
            os.remove(temp_script)
        except:
            pass

        # Extract result from output
        output = process.stdout
        if "AGENT_RESULT_START" in output and "AGENT_RESULT_END" in output:
            start_idx = output.find("AGENT_RESULT_START") + len("AGENT_RESULT_START\n")
            end_idx = output.find("AGENT_RESULT_END")
            result_text = output[start_idx:end_idx].strip()

            return {
                "status": "success",
                "agent": "database_analyst",
                "result": result_text,
                "task": task_description
            }
        else:
            # Agent failed or returned unexpected output
            return {
                "status": "error",
                "agent": "database_analyst",
                "error": f"Unexpected output from agent. Stdout: {output[:500]}",
                "stderr": process.stderr[:500] if process.stderr else "",
                "task": task_description
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "agent": "database_analyst",
            "error": "Agent timeout - task took longer than 60 seconds",
            "task": task_description
        }
    except Exception as e:
        return {
            "status": "error",
            "agent": "database_analyst",
            "error": str(e),
            "task": task_description
        }


@ai_function(
    name="translate_text",
    description="Translate text between English and Czech by invoking the specialized translation agent. Use for translation requests."
)
def translate_text(text: str, target_language: Optional[str] = None) -> dict:
    """
    Invoke translation agent to translate text.

    Args:
        text: The text to translate
        target_language: Target language ('czech' or 'english'). Auto-detect if not specified.

    Returns:
        Dictionary with translation result
    """
    try:
        # Create translation task script
        script = f"""
import asyncio
import sys
import os
from agent_framework import ChatAgent, ChatMessage
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

load_dotenv()

async def run_task():
    model = OpenAIChatClient(
        api_key="ollama",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/"),
        model_id="jobautomation/OpenEuroLLM-Czech",
    )

    agent = ChatAgent(
        chat_client=model,
        instructions='''You are a professional translator specializing in English and Czech translations.
Translate the provided text accurately and naturally.''',
        tools=[],
    )

    thread = agent.get_new_thread()

    task = '''Translate this text: {text}'''
    messages = [ChatMessage(role="user", text=task)]
    result = await agent.run(messages, thread=thread)

    print("AGENT_RESULT_START")
    print(result.text)
    print("AGENT_RESULT_END")

asyncio.run(run_task())
"""

        # Write temporary script
        temp_script = os.path.join(os.path.dirname(__file__), "_temp_translate_task.py")
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(script)

        # Run the agent as subprocess
        process = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(__file__)
        )

        # Clean up
        try:
            os.remove(temp_script)
        except:
            pass

        # Extract result
        output = process.stdout
        if "AGENT_RESULT_START" in output and "AGENT_RESULT_END" in output:
            start_idx = output.find("AGENT_RESULT_START") + len("AGENT_RESULT_START\n")
            end_idx = output.find("AGENT_RESULT_END")
            result_text = output[start_idx:end_idx].strip()

            return {
                "status": "success",
                "agent": "translator",
                "result": result_text,
                "original_text": text
            }
        else:
            return {
                "status": "error",
                "agent": "translator",
                "error": f"Unexpected output. Stdout: {output[:500]}",
                "stderr": process.stderr[:500] if process.stderr else ""
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "agent": "translator",
            "error": "Translation timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "agent": "translator",
            "error": str(e)
        }


async def main():
    print("=" * 60)
    print("=== AI SUPERVISOR AGENT - Multi-Agent Orchestration ===")
    print("=" * 60)
    print("\nConnecting to Ollama server...\n")

    # Create OpenAI client for Ollama with supervisor model
    supervisor_model = OpenAIChatClient(
        api_key="ollama",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/"),
        model_id=os.getenv("SUPERVISOR_MODEL", "qwen2.5:7b"),
    )

    # Supervisor tools - delegation only
    supervisor_tools = [
        query_database,
        translate_text
    ]

    print(f"✓ Loaded {len(supervisor_tools)} delegation tools")
    print(f"  - query_database: Invokes database analyst agent")
    print(f"  - translate_text: Invokes translation agent\n")

    # Create supervisor agent
    supervisor = ChatAgent(
        chat_client=supervisor_model,
        instructions="""You are a SUPERVISOR AGENT that orchestrates specialized AI agents via subprocess invocation.

Available agents:

1. **Database Analyst Agent** (via query_database tool)
   - Handles: Database queries, log analysis, error investigation
   - Tools: select_from_table, get_tables, execute_stored_procedure
   - When to use: ANY database-related task
   - Example tasks:
     - "Find last record in ErrorLog table"
     - "Show all tables in database"
     - "Analyze error in latest log entry"

2. **Translation Agent** (via translate_text tool)
   - Handles: English ↔ Czech translation
   - When to use: Translation requests
   - Example: "Translate 'Hello' to Czech"

Your responsibilities:
- Analyze user requests
- Decide which agent to invoke
- Call the appropriate tool (query_database or translate_text)
- Present results from the agent to the user
- Communicate in the same language as user (Czech/English)

Decision rules:
- Database/logs/errors? → Use query_database tool
- Translation? → Use translate_text tool
- General question? → Answer directly

IMPORTANT:
- For database tasks, ALWAYS use query_database tool
- Provide clear task descriptions to agents
- Present agent results clearly to user
- If agent returns error, explain it to user""",
        tools=supervisor_tools,
    )

    # Create conversation thread
    thread = supervisor.get_new_thread()

    print("=" * 60)
    print("SUPERVISOR AGENT IS READY!")
    print("=" * 60)
    print("\nOrchestration mode: SUBPROCESS DELEGATION")
    print("\nSpecialized agents:")
    print("  1. Database Analyst Agent (MS SQL)")
    print("  2. Translation Agent (EN ↔ CZ)")
    print("\nType 'exit' to quit, 'help' for examples\n")

    # Main loop
    while True:
        user_input = input("You: ")

        if not user_input.strip():
            continue

        if user_input.strip().lower() == "exit":
            print("\nShutting down supervisor agent...")
            break

        if user_input.strip().lower() == "help":
            print("\n" + "=" * 60)
            print("EXAMPLE COMMANDS:")
            print("=" * 60)
            print("Database queries (delegated to DB agent):")
            print("  - 'Show me all tables in database'")
            print("  - 'Najdi poslední záznam v tabulce ErrorLog'")
            print("  - 'Find errors in logs from today'")
            print("  - 'Analyzuj chybu v posledním záznamu'")
            print("\nTranslation (delegated to translator):")
            print("  - 'Translate: Hello, how are you?'")
            print("  - 'Přelož do angličtiny: Dobrý den'")
            print("\nGeneral:")
            print("  - 'What can you do?'")
            print("  - 'Co umíš?'")
            print("=" * 60 + "\n")
            continue

        print("Supervisor: ", end="", flush=True)

        try:
            # Create message and get response
            messages = [ChatMessage(role="user", text=user_input)]
            result = await supervisor.run(messages, thread=thread)
            print(result.text)
            print()

        except Exception as ex:
            print(f"\n[ERROR] Supervisor failed: {ex}")
            print("Check if Ollama server is running at http://localhost:11434")
            print(f"and model '{os.getenv('SUPERVISOR_MODEL', 'qwen2.5:7b')}' is installed.")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    asyncio.run(main())
