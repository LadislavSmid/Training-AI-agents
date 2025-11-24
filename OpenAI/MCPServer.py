"""
MCP Server pro AI Agent
Poskytuje tools pro získávání informací o akciích
"""

import yfinance as yf
import json
from typing import Dict, Any, List
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio


class MCPStockServer:
    """MCP Server pro práci s akciovými daty"""
    
    def __init__(self):
        self.server = Server("stock-tools-server")
        self.tools_list = [
            Tool(
                name="get_stock_price",
                description="Získá aktuální cenu akcie podle burzovního symbolu (např. AAPL pro Apple, MSFT pro Microsoft, TSLA pro Tesla)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Burzovní symbol akcie (např. AAPL, MSFT, GOOGL)"
                        }
                    },
                    "required": ["symbol"]
                }
            )
        ]
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Nastavení handlerů pro MCP server"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Vrací seznam dostupných nástrojů"""
            return self.tools_list
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Volání nástroje podle jména"""
            if name == "get_stock_price":
                result = self.get_stock_price(arguments.get("symbol"))
                return [TextContent(type="text", text=json.dumps(result))]
            else:
                raise ValueError(f"Neznámý nástroj: {name}")
    
    async def get_tools(self) -> List[Tool]:
        """Veřejná metoda pro získání seznamu nástrojů"""
        return self.tools_list
    
    async def call_tool_method(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Veřejná metoda pro volání nástroje"""
        if name == "get_stock_price":
            return self.get_stock_price(arguments.get("symbol"))
        else:
            raise ValueError(f"Neznámý nástroj: {name}")
    
    def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Získá aktuální cenu akcie podle symbolu"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            if current_price is None:
                # Pokusíme se získat poslední zavírací cenu
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
    
    async def run(self):
        """Spustí MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


# Pro přímé spuštění MCP serveru
if __name__ == "__main__":
    import asyncio
    
    server = MCPStockServer()
    asyncio.run(server.run())
