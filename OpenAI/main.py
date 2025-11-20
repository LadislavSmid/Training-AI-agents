import openai
from openai import OpenAI
import yfinance as yf
import json
import os
from dotenv import load_dotenv

# Načtení proměnných prostředí z .env souboru
load_dotenv()

# Inicializace OpenAI klienta
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Definice dostupných funkcí
def get_stock_price(symbol):
    """Získá aktuální cenu akcie podle symbolu"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None:
           
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
        
        if current_price:
            return {
                "symbol": symbol,
                "price": round(current_price, 2),
                "currency": info.get('currency', 'USD'),
                "name": info.get('longName', symbol)
            }
        else:
            return {"error": f"Nepodařilo se získat cenu pro symbol {symbol}"}
    except Exception as e:
        return {"error": f"Chyba při získávání ceny: {str(e)}"}

# Definice tools pro OpenAI
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Získá aktuální cenu akcie podle burzovního symbolu (např. AAPL pro Apple, MSFT pro Microsoft, TSLA pro Tesla)",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Burzovní symbol akcie (např. AAPL, MSFT, GOOGL)"
                    }
                },
                "required": ["symbol"]
            }
        }
    }
]

# Mapa funkcí pro volání
available_functions = {
    "get_stock_price": get_stock_price
}

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
                    
                    # Provedeme všechny požadované volání funkcí
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Zavoláme příslušnou funkci
                        if function_name in available_functions:
                            function_response = available_functions[function_name](**function_args)
                            
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