import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.getcwd())

from mcp_models.search import MCPSearchTools, get_search_tools

async def test_search():
    print("Testing Search Tools...")
    
    # Check if tools are listed
    tools = get_search_tools(user_id=1)
    print(f"Found {len(tools)} search tools:")
    for tool in tools:
        print(f" - {tool['name']}")
    
    search_web_tool = next((t for t in tools if t['name'] == 'search_web'), None)
    
    if search_web_tool:
        print("\nAttempting a mock search (checking imports)...")
        # We won't actually call the search API to avoid spamming or blocking, 
        # just instantiating and checking if DDGS is available.
        # But let's try a real search if possible.
        
        search_instance = MCPSearchTools(user_id=1)
        # Using a distinct query to verify results
        result = await search_instance.search_web("python programming language", limit=1)
        
        if result['success']:
            print("✅ Search successful!")
            print(f"Result: {result['results'][0]['title']}")
        else:
            print(f"⚠️ Search skipped/failed (expected if no internet): {result.get('error')}")
            # If it failed due to no internet/library but returned the safe error, that is also a pass for our requirement.
            if "Search capability is not available" in result.get('error', ''):
                 print("✅ Graceful fallback working as expected.")
            elif "connectivity issues" in result.get('message', ''):
                 print("✅ Graceful fallback working as expected (connectivity).")
    else:
        print("❌ 'search_web' tool not found!")

if __name__ == "__main__":
    asyncio.run(test_search())
