"""
MCP Search Tools

This module provides MCP (Model Context Protocol) tools for web search using DuckDuckGo.
Includes web search, image search, and news search.
"""

from typing import Any, Dict, List, Optional
import asyncio

# specific imports request by user to be safe
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


class MCPSearchTools:
    """MCP server providing search tools via DuckDuckGo."""
    
    def __init__(self, user_id: int):
        """Initialize MCP Search Tools."""
        self.user_id = user_id
    
    async def search_web(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Perform a general web search."""
        if not DDGS_AVAILABLE:
            return {
                'success': False,
                'error': 'Search capability is not available (duckduckgo-search not installed).'
            }
            
        try:
            def _do_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=limit))
            
            # Run in thread to allow async execution
            results = await asyncio.to_thread(_do_search)
            
            return {
                'success': True,
                'results': results,
                'count': len(results),
                'message': f"Found {len(results)} web results for '{query}'"
            }
        except Exception as e:
            # Graceful error handling as requested
            return {
                'success': False, 
                'error': f"Search failed: {str(e)}", 
                'message': "Could not perform search largely due to connectivity issues."
            }

    async def search_images(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Perform an image search."""
        if not DDGS_AVAILABLE:
            return {
                'success': False,
                'error': 'Search capability is not available (duckduckgo-search not installed).'
            }
            
        try:
            def _do_search():
                with DDGS() as ddgs:
                    return list(ddgs.images(query, max_results=limit))
            
            results = await asyncio.to_thread(_do_search)
            
            formatted_results = []
            for r in results:
                formatted_results.append({
                    'title': r.get('title'),
                    'image': r.get('image'),
                    'thumbnail': r.get('thumbnail'),
                    'url': r.get('url'),
                    'source': r.get('source')
                })
            
            return {
                'success': True,
                'results': formatted_results,
                'count': len(formatted_results),
                'message': f"Found {len(formatted_results)} images for '{query}'"
            }
        except Exception as e:
            return {
                'success': False, 
                'error': f"Image search failed: {str(e)}",
                'message': "Could not perform image search largely due to connectivity issues."
            }

    async def search_news(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Perform a news search."""
        if not DDGS_AVAILABLE:
            return {
                'success': False,
                'error': 'Search capability is not available (duckduckgo-search not installed).'
            }
            
        try:
            def _do_search():
                with DDGS() as ddgs:
                    return list(ddgs.news(query, max_results=limit))
            
            results = await asyncio.to_thread(_do_search)
            
            return {
                'success': True,
                'results': results,
                'count': len(results),
                'message': f"Found {len(results)} news items for '{query}'"
            }
        except Exception as e:
            return {
                'success': False, 
                'error': f"News search failed: {str(e)}",
                'message': "Could not perform news search largely due to connectivity issues."
            }


def get_search_tools(user_id: int) -> List[Dict[str, Any]]:
    """Get available search MCP tools."""
    tools_instance = MCPSearchTools(user_id)
    
    return [
        {
            'name': 'search_web',
            'description': 'Search the web for information using DuckDuckGo. Use this to find current events, documentation, or general knowledge.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Search query'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max results (default 5)'
                    }
                },
                'required': ['query']
            },
            'function': tools_instance.search_web
        },
        {
            'name': 'search_images',
            'description': 'Search for images. Returns URLs to images and thumbnails.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Search query'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max results (default 5)'
                    }
                },
                'required': ['query']
            },
            'function': tools_instance.search_images
        },
        {
            'name': 'search_news',
            'description': 'Search for recent news articles.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Search query'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max results (default 5)'
                    }
                },
                'required': ['query']
            },
            'function': tools_instance.search_news
        }
    ]


async def execute_search_tool(user_id: int, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a search MCP tool by name."""
    tools_instance = MCPSearchTools(user_id)
    
    if tool_name == 'search_web':
        return await tools_instance.search_web(**parameters)
    elif tool_name == 'search_images':
        return await tools_instance.search_images(**parameters)
    elif tool_name == 'search_news':
        return await tools_instance.search_news(**parameters)
    else:
        return {
            'success': False,
            'error': f"Unknown search tool: {tool_name}"
        }
