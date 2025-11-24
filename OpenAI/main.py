import openai
from openai import OpenAI
import json
import os
from dotenv import load_dotenv
from MCPServer import MCPStockServer
import asyncio

# Načtení proměnných prostředí z .env souboru
load_dotenv()

# Inicializace OpenAI klienta
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Inicializace MCP serveru (běží v rámci aplikace)
mcp_server = MCPStockServer()

# Získání tools z MCP serveru pro OpenAI
async def get_tools_from_mcp():
    """Získá definice tools z MCP serveru a převede je na OpenAI formát"""
    tools_list = await mcp_server.get_tools()
    
    openai_tools = []
    for tool in tools_list:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        })
    return openai_tools

# Získání tools při startu
tools = asyncio.run(get_tools_from_mcp())

# Funkce pro volání MCP serveru
async def call_mcp_tool(tool_name: str, arguments: dict):
    """Volá nástroj na MCP serveru"""
    return await mcp_server.call_tool_method(tool_name, arguments)

def call_tool_sync(tool_name: str, arguments: dict):
    """Synchronní wrapper pro volání MCP tools"""
    return asyncio.run(call_mcp_tool(tool_name, arguments))

class AIAgent:
    def __init__(self, client, model="gpt-4"):
        self.client = client
        self.model = model
        self.conversation_history = []
        self.max_iterations = 15  # Maximální počet iterací pro volání funkcí
    
    def add_message(self, role, content):
        """Přidá zprávu do historie konverzace"""
        self.conversation_history.append({"role": role, "content": content})
    
    def chat(self, user_message):
        """Pošle zprávu agentovi a vrátí odpověď"""
        self.add_message("user", user_message)
        
        try:
            iterations = 0
            while iterations < self.max_iterations:
                iterations += 1

                # Volání API s možností použití tools
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=tools,
                    tool_choice="auto"
                )
            
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
            
                # Pokud AI chce zavolat funkci
                if tool_calls:
                    
                    self.conversation_history.append(response_message)
                    
                    # Provedeme všechny požadované volání funkcí přes MCP server
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Zavoláme funkci přes MCP server
                        function_response = call_tool_sync(function_name, function_args)
                        
                        # Přidáme výsledek funkce do historie
                        self.conversation_history.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(function_response)
                        })
                    continue  # Pokračujeme v cyklu pro další odpověď AI        
                else:
                    # Pokud AI nechtěla zavolat funkci, vrátíme běžnou odpověď
                    assistant_message = response_message.content
                    self.add_message("assistant", assistant_message)
                    
                    return assistant_message
            return "Dosáhli jsme maximálního počtu iterací bez získání odpovědi."
        except Exception as e:
            return f"Chyba: {str(e)}"
    
    def reset_conversation(self):
        """Resetuje historii konverzace"""
        self.conversation_history = []


# Použití agenta
if __name__ == "__main__":

    agent = AIAgent(client, model="gpt-4")
    

    print("AI Agent je připraven. Napište 'exit' pro ukončení.\n")
    
    while True:
        user_input = input("Vy: ")
        if user_input.lower() == 'exit':
            break
        
        response = agent.chat(user_input)
        print(f"Agent: {response}\n")