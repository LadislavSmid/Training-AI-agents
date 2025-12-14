# Multi-Agent System with Microsoft Agent Framework

This project implements a multi-agent architecture using Microsoft Agent Framework with local Ollama models.

## Architecture

### Supervisor Pattern

The system uses a **Supervisor Agent** that coordinates specialized agents:

```
┌─────────────────────────────────────┐
│      SUPERVISOR AGENT               │
│   (DeepSeek-R1-Distill-Qwen)       │
│                                     │
│  - Task analysis & routing          │
│  - Agent coordination               │
│  - Multi-step orchestration         │
└──────────┬──────────────────────────┘
           │
           ├─────────────┬─────────────────┐
           ▼             ▼                 ▼
    ┌──────────┐  ┌─────────────┐  ┌──────────────┐
    │Translation│  │Database     │  │Future agents │
    │Agent      │  │Analyst Agent│  │...           │
    └──────────┘  └─────────────┘  └──────────────┘
```

## Agents

### 1. Supervisor Agent (`supervisor_agent.py`)
- **Model**: Qwen2.5 (7B) - supports tool/function calling
- **Purpose**: Main orchestrator that routes tasks to specialized agents
- **Capabilities**:
  - Analyzes user requests
  - Delegates to appropriate specialized agents
  - Handles general queries directly
  - Coordinates multi-agent workflows
  - Bilingual (English & Czech)

### 2. Database Analyst Agent (`agent.py`)
- **Model**: gpt-oss:latest
- **Purpose**: MS SQL Server database operations and log analysis
- **Tools**:
  - `select_from_table` - Query tables with filtering
  - `get_tables` - List all database tables
  - `execute_stored_procedure` - Run stored procedures
- **Use cases**: Error analysis, log queries, data retrieval

### 3. Translation Agent (`translator_agent.py`)
- **Model**: jobautomation/OpenEuroLLM-Czech
- **Purpose**: English ↔ Czech translation
- **Capabilities**:
  - Auto-detect source language
  - Natural, contextual translation
  - Technical terminology handling
  - Preserves tone and style

## Installation

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Ollama models

```bash
# Supervisor model (MUST support tool/function calling)
ollama pull qwen2.5:7b                  # Recommended
# Alternatives: llama3.2:latest, mistral:latest

# Database analyst model
ollama pull gpt-oss:latest

# Translation model
ollama pull jobautomation/OpenEuroLLM-Czech
```

### 3. Configure environment

Copy and edit `.env` file with your database credentials:

```bash
# Database connection
DB_SERVER=your-server
DB_NAME=your-database
DB_USER=your-username
DB_PASSWORD=your-password

# Models
SUPERVISOR_MODEL=qwen2.5:7b
OPENAI_MODEL_ID=gpt-oss:latest
TRANSLATOR_MODEL=jobautomation/OpenEuroLLM-Czech
```

## Usage

### Start Supervisor (Recommended)

The supervisor agent handles all incoming requests and delegates to specialized agents:

```bash
python supervisor_agent.py
```

**Example interactions:**

```
You: Show me all tables in the database
Supervisor: [Delegates to database analyst or uses direct database access]

You: Přelož do angličtiny: Dobrý den, jak se máte?
Supervisor: [Delegates to translation agent]

You: What can you do?
Supervisor: [Handles directly]
```

### Run Specialized Agents Directly

#### Database Analyst
```bash
python agent.py
```

#### Translator
```bash
python translator_agent.py
```

## Configuration Files

- **`.env`** - Environment variables (database, models)
- **`requirements.txt`** - Python dependencies
- **`server.py`** - MCP server with database tools

## Model Recommendations

### Supervisor Model Options

**IMPORTANT**: Supervisor model MUST support tool/function calling!

1. **Qwen2.5 (7B or 32B)** ⭐ Recommended
   - Full tool/function calling support
   - Czech language support
   - Long context (128K tokens)
   - Good reasoning capabilities
   - `ollama pull qwen2.5:7b`

2. **Llama 3.2 (3B or 8B)**
   - Optimized for agentic tasks
   - Excellent tool-calling support
   - Fast and efficient
   - `ollama pull llama3.2:latest`

3. **Mistral (7B)**
   - Strong tool-calling capabilities
   - Good multilingual support
   - Fast inference
   - `ollama pull mistral:latest`

**NOT recommended for supervisor**:
- ❌ DeepSeek-R1 (no tool calling support)
- ❌ GPT-OSS (limited tool calling)

### Hardware Requirements

| Model | VRAM | RAM | Speed | Tool Calling |
|-------|------|-----|-------|--------------|
| Qwen2.5 7B | 4-8GB | 8GB+ | Fast | ✅ Yes |
| Llama 3.2 3B | 2-4GB | 4GB+ | Very Fast | ✅ Yes |
| Llama 3.2 8B | 4-8GB | 8GB+ | Fast | ✅ Yes |
| Mistral 7B | 4-8GB | 8GB+ | Fast | ✅ Yes |
| GPT-OSS 20B | 12-20GB | 16GB+ | Slower | ⚠️ Limited |

## Architecture Patterns

### Delegation Pattern

The supervisor uses delegation tools to route tasks:

```python
@ai_function(name="delegate_to_translator")
def delegate_to_translator(text: str, target_language: Optional[str] = None):
    # Routes translation tasks to specialist
    pass

@ai_function(name="delegate_to_database_analyst")
def delegate_to_database_analyst(query_description: str):
    # Routes database tasks to specialist
    pass
```

### Future Extensions

To add new specialized agents:

1. Create new agent file (e.g., `email_agent.py`)
2. Add delegation tool in `supervisor_agent.py`:
   ```python
   @ai_function(name="delegate_to_email_agent")
   def delegate_to_email_agent(task: str):
       pass
   ```
3. Update supervisor instructions to include new agent
4. Add model configuration to `.env`

## Troubleshooting

### Ollama connection issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama (if not running)
ollama serve
```

### Database connection issues
- Verify credentials in `.env`
- Check SQL Server is accessible
- Verify ODBC driver is installed: `odbcinst -q -d`

### Model not found
```bash
# List installed models
ollama list

# Pull missing model
ollama pull <model-name>
```

## Security Notes

⚠️ **IMPORTANT**:
- `.env` file is in `.gitignore` - never commit credentials
- Database credentials are sensitive - use environment variables
- SQL injection protection: Use parameterized queries only

## License

This project uses Microsoft Agent Framework and is subject to its license terms.
