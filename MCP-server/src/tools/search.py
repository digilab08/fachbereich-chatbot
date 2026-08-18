from typing import List, Optional
from xml.sax.saxutils import escape
from fastmcp import FastMCP
from services.qdrant_svc import QdrantService

def register_search_tools(mcp: FastMCP, qdrant_svc: QdrantService) -> None:
    """
    Register search-related tools on the given FastMCP server instance.
    
    :param mcp: The FastMCP server instance.
    :param qdrant_svc: The Qdrant service used for vector search.
    """
    
    @mcp.tool()
    async def search_notes(query: str, degree_program_code: str) -> str:
        """
        Perform a hybrid semantic search over the markdown notes.
        
        This tool searches for university specific information based on the user's degree program code. 
        
        :param query: The search query text, usually a question about university policies or procedures.
        :param degree_program_code: The code for the degree program to filter by. Usually, this is a three-letter code like "BWL" or "BWI".
        :return: A formatted string containing the search results to be read by the LLM.
        """
        results = await qdrant_svc.search_hybrid(
            query_text=query,
            target_tags=[degree_program_code, "FB08"]
        )
        
        if not results:
            return "<search_results count='0'><message>No relevant notes found for your query.</message></search_results>"
        
        # Format the results into an XML string for structured parsing by the LLM
        response_lines = ["<search_results>"]
        for idx, point in enumerate(results, 1):
            payload = point.payload or {}
            source = payload.get("source", "Unknown source")
            url = payload.get("url", "")
            headings = payload.get("headings") or []
            text = payload.get("text", "")

            response_lines.append(f"  <result index='{idx}'>")
            response_lines.append(f"    <source>{escape(str(source))}</source>")
            if url:
                response_lines.append(f"    <url>{escape(str(url))}</url>")
            if headings:
                headings_text = ", ".join(str(heading) for heading in headings)
                response_lines.append(f"    <headings>{escape(headings_text)}</headings>")
            response_lines.append(f"    <content>{escape(str(text))}</content>")
            response_lines.append("  </result>")
        
        response_lines.append("</search_results>")
        return "\n".join(response_lines)