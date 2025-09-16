I will make use a tool known as fastmcp.cloud to generate the backend. This will give me a server url to input to ai models, provided I give it acess to my python file in the proper format.

An example of the proper formatting is below.

"""
FastMCP Reverse Server
"""

from fastmcp import FastMCP

# Create server
mcp = FastMCP("Reverse Server")

@mcp.tool
def reverse_tool(text: str) -> str:
    """Echo the input text (reversed)"""
    return text[::-1]

if __name__ == "__main__":
    mcp.run()
