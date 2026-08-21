from xml.sax.saxutils import escape
from fastmcp import FastMCP
from services.qdrant_svc import QdrantService
from services.study_programs_svc import study_program_exists, get_categories


def improve_url(url: str, page: str | None) -> str:
    if not url:
        return ""

    if url.endswith("?forcedownload=1"):
        url = url[:-len("?forcedownload=1")]
    
    if page:
        url += f"#page={page}"

    return url

def register_search_tools(mcp: FastMCP, qdrant_svc: QdrantService) -> None:
    """
    Register search-related tools on the given FastMCP server instance.
    
    :param mcp: The FastMCP server instance.
    :param qdrant_svc: The Qdrant service used for vector search.
    """
    
    @mcp.tool()
    async def search_university_information(query: str, degree_program_abbreviation: str) -> str:
        """
        Perform a hybrid semantic search over university_information based on the user's degree program code. 
        
        :param query: The search query text, usually a question about university policies or procedures.
        :param degree_program_abbreviation: The code for the degree program to filter by. Usually, this is a three-letter code like "BWL" or "BWI".
        :return: A formatted string containing the search results.
        """
        if not study_program_exists(degree_program_abbreviation):
            return f"Error: The degree program code '{degree_program_abbreviation}' is not recognized. Probably use another tool to check which programs are available or ask the user for clarification."

        target_tags = get_categories(degree_program_abbreviation)

        try:
            results = await qdrant_svc.search_hybrid(
                query_text=query,
                target_tags=target_tags
            )
        except Exception as e:
            return "Error: An error occurred while searching for university information."
        
        if not results:
            return "<message>No relevant university information found for your query.</message>"
        
        # Format the results into an XML string for structured parsing by the LLM
        response_lines = ["<search_results>"]
        for idx, point in enumerate(results, 1):
            payload = point.payload or {}
            source = payload.get("source", "Unknown source")
            url = improve_url(payload.get("url", ""), payload.get("page_number"))
            headings = payload.get("headings") or []
            text = payload.get("text", "")

            url_param = f" url='{escape(str(url))}'" if url else ""
            headings_param = f" headings='{escape(' > '.join(str(h) for h in headings))}'" if headings else ""

            response_lines.append(f"  <result index='{idx}' source='{escape(str(source))}{url_param}{headings_param}'>")
  
            response_lines.append(f"    {escape(str(text))}")
            response_lines.append("  </result>")
        
        response_lines.append("</search_results>")
        return "\n".join(response_lines)