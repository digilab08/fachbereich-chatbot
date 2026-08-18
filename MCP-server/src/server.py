from fastmcp import FastMCP

from services.qdrant_svc import QdrantService
from services.embed_svc import EmbeddingService
from tools.search import register_search_tools

qdrant_service = QdrantService(
    collection_name="test",
    qdrant_url="http://localhost:6333",
    embed_svc=EmbeddingService()
)



mcp = FastMCP("HSNR-FB08-MCP")

register_search_tools(mcp=mcp, qdrant_svc=qdrant_service)

if __name__ == "__main__":
  # Wichtig: transport="sse", host="0.0.0.0" und Port festlegen
  mcp.run()