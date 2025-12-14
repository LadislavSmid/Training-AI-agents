"""
MCP Server for Microsoft SQL Server Database Operations

This server provides tools for querying MS SQL Server databases using the Model Context Protocol (MCP)
and Microsoft Agent Framework.
"""

import os
import pyodbc
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass
from agent_framework import ai_function


@dataclass
class DatabaseConfig:
    """Configuration for MS SQL Server database connection."""
    server: str = "localhost"
    port: str = "1433"
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    driver: str = "ODBC Driver 18 for SQL Server"
    use_windows_auth: bool = False
    trust_cert: bool = True
    encrypt: str = "no"  # no, yes, optional


class MSSQLConnection:
    """Manages MS SQL Server database connections."""
    
    def __init__(self, config: DatabaseConfig):
        self.server = config.server
        self.port = config.port
        self.database = config.database
        self.username = config.username
        self.password = config.password
        self.driver = config.driver
        self.use_windows_auth = config.use_windows_auth
        self.trust_cert = config.trust_cert
        self.encrypt = config.encrypt
        
    def get_connection_string(self) -> str:
        """Build connection string based on configuration."""
        conn_parts = [
            f"DRIVER={{{self.driver}}}",
            f"SERVER={self.server},{self.port}",
            f"DATABASE={self.database}"
        ]
        
        if self.use_windows_auth:
            conn_parts.append("Trusted_Connection=yes")
        else:
            conn_parts.append(f"UID={self.username}")
            conn_parts.append(f"PWD={self.password}")
        
        # Encryption settings
        conn_parts.append(f"Encrypt={self.encrypt}")
        
        if self.trust_cert and self.encrypt != "no":
            conn_parts.append("TrustServerCertificate=yes")
        
        return ";".join(conn_parts)
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries."""
        try:
            conn_string = self.get_connection_string()
            with pyodbc.connect(conn_string) as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Get column names
                columns = [column[0] for column in cursor.description] if cursor.description else []
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries with JSON-serializable values
                results = []
                for row in rows:
                    row_dict = {}
                    for col_name, value in zip(columns, row):
                        # Convert datetime objects to ISO format strings
                        if isinstance(value, (datetime, date)):
                            row_dict[col_name] = value.isoformat()
                        else:
                            row_dict[col_name] = value
                    results.append(row_dict)
                
                return results
                
        except Exception as e:
            return [{"error": str(e)}]


# Global database connection (will be initialized when get_all_mcp_tools is called)
db: Optional[MSSQLConnection] = None

# Registry for MCP tools - automatically populated by decorated functions
_MCP_TOOLS_REGISTRY = []


# MCP Tools using Microsoft Agent Framework decorators
@ai_function(
    name="select_from_table",
    description="Execute a SELECT query on a specified table with optional filtering, sorting, and limit.",
)
def select_from_table(
    table_name: str,
    limit: Optional[int] = None,
    condition: Optional[str] = None,
    order_by: Optional[str] = None
) -> dict:
    """Execute a SELECT query on a specified table.
    
    Args:
        table_name: Name of the table to query (required).
        limit: Maximum number of rows to return.
        condition: WHERE clause condition (without the WHERE keyword).
        order_by: ORDER BY clause (without the ORDER BY keyword).
    
    Returns:
        A dictionary containing:
            - 'results': List of rows as dictionaries, or error information.
            - 'count': Number of rows returned.
            - 'query': The executed SQL query.
    """
    try:
        # Build the query
        query = "SELECT "
        
        if limit:
            query += f"TOP {limit} "
        
        query += f"* FROM {table_name}"
        
        if condition:
            query += f" WHERE {condition}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # Execute query
        results = db.execute_query(query)
        
        # Check for errors
        if results and "error" in results[0]:
            return {
                "results": [],
                "count": 0,
                "error": results[0]["error"],
                "query": query
            }
        
        return {
            "results": results,
            "count": len(results),
            "query": query
        }
        
    except Exception as e:
        return {
            "results": [],
            "count": 0,
            "error": str(e),
            "query": query if 'query' in locals() else "N/A"
        }

# Register the tool
_MCP_TOOLS_REGISTRY.append(select_from_table)


@ai_function(
    name="get_tables",
    description="Get a list of all tables in the database.",
)
def get_tables() -> dict:
    """Get a list of all tables in the database.
    
    Returns:
        A dictionary containing:
            - 'tables': List of table names with schema (e.g., 'dbo.Users').
            - 'count': Number of tables found.
    """
    try:
        query = """
        SELECT 
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        
        results = db.execute_query(query)
        
        # Check for errors
        if results and "error" in results[0]:
            return {
                "tables": [],
                "count": 0,
                "error": results[0]["error"]
            }
        
        # Simplify output to just table names with schema
        tables = [f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}" for row in results if 'TABLE_SCHEMA' in row]
        
        return {
            "tables": tables,
            "count": len(tables)
        }
        
    except Exception as e:
        return {
            "tables": [],
            "count": 0,
            "error": str(e)
        }

# Register the tool
_MCP_TOOLS_REGISTRY.append(get_tables)


@ai_function(
    name="execute_stored_procedure",
    description="Execute a stored procedure with optional parameters.",
)
def execute_stored_procedure(
    procedure_name: str,
    parameters: Optional[Dict[str, Any]] = None
) -> dict:
    """Execute a stored procedure with parameters.
    
    Args:
        procedure_name: Name of the stored procedure (e.g., 'dbo.GetUserById' or 'GetUserById').
        parameters: Dictionary of parameter names and values (e.g., {'UserId': 123, 'Active': True}).
    
    Returns:
        A dictionary containing:
            - 'results': List of rows returned by the procedure (if any).
            - 'count': Number of rows returned.
            - 'return_value': Return value from the procedure (if any).
            - 'procedure': The executed procedure name.
    """
    try:
        # Build the EXEC statement
        if parameters and len(parameters) > 0:
            # Build parameter placeholders
            param_placeholders = ", ".join([f"@{key} = ?" for key in parameters.keys()])
            query = f"EXEC {procedure_name} {param_placeholders}"
            param_values = tuple(parameters.values())
        else:
            query = f"EXEC {procedure_name}"
            param_values = None
        
        # Execute procedure
        results = db.execute_query(query, param_values)
        
        # Check for errors
        if results and "error" in results[0]:
            return {
                "results": [],
                "count": 0,
                "error": results[0]["error"],
                "procedure": procedure_name,
                "query": query
            }
        
        return {
            "results": results,
            "count": len(results),
            "procedure": procedure_name,
            "query": query
        }
        
    except Exception as e:
        return {
            "results": [],
            "count": 0,
            "error": str(e),
            "procedure": procedure_name,
            "query": query if 'query' in locals() else "N/A"
        }

# Register the tool
_MCP_TOOLS_REGISTRY.append(execute_stored_procedure)


def get_all_mcp_tools(config: DatabaseConfig) -> List[callable]:
    """
    Get all registered MCP tools from this server.
    
    Args:
        config: DatabaseConfig object with connection parameters
    
    Returns:
        List of all MCP tool functions registered in _MCP_TOOLS_REGISTRY
    """
    global db
    db = MSSQLConnection(config)
    return _MCP_TOOLS_REGISTRY.copy()


if __name__ == "__main__":
    # Test the connection and tools
    from dotenv import load_dotenv
    load_dotenv()
    
    print("MS SQL MCP Server")
    print("=" * 50)
    print("\nTesting connection...")
    
    # Create test configuration from environment variables
    test_config = DatabaseConfig(
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
    
    # Get tools with configuration
    available_tools = get_all_mcp_tools(test_config)
    
    # Test get_tables
    print("\nTesting get_tables():")
    tables_result = get_tables()
    print(f"Found {tables_result.get('count', 0)} tables")
    if 'error' in tables_result:
        print(f"Error: {tables_result['error']}")
    else:
        print(f"Tables: {tables_result.get('tables', [])[:5]}...")  # Show first 5
    
    print("\nMCP Server is ready!")
    print("Available tools:")
    for tool in available_tools:
        # AIFunction object has 'name' attribute instead of '__name__'
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', 'unknown'))
        tool_desc = getattr(tool, 'description', 'No description')
        print(f"  - {tool_name}: {tool_desc}")


