import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from fastmcp import FastMCP

from services.qdrant_svc import QdrantService
from services.embed_svc import EmbeddingService
from tools.search import register_search_tools
from tools.static_info import register_static_info_tools
from tools.file_access import register_file_access_tools

from utils import get_logger

load_dotenv()
logger = get_logger(__name__)
logger.debug("Initializing MCP server module.")


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable container for all pipeline configuration values.

    The values are read from environment variables at construction time and
    fall back to sensible defaults for local development.

    :param extraction_config_path: Path to the CSV file describing which
        source paths to include and how to map them to targets.
    :param data_path: Root directory of the raw downloaded data.
    :param processed_folder_path: Directory where converted markdown files
        are persisted between runs.
    :param moodle_url: Base URL of the Moodle instance, used to build
        fallback URLs for files without a direct content URL.
    :param collection_name: Name of the Qdrant collection to write to.
    :param qdrant_url: URL of the Qdrant instance to connect to.
    :param dense_model_name: Name of the dense embedding model.
    :param sparse_model_name: Name of the sparse embedding model.
    :param transport: MCP transport mode.
    :param host: Host on which the MCP server listens.
    :param port: Port on which the MCP server listens.
    :param mcp_server_name: Name of the MCP server instance.
    """

    data_dir: str
    config_dir: str
    collection_name: str
    qdrant_url: str
    dense_model_name: str
    sparse_model_name: str
    host: str
    port: int
    mcp_server_name: str

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Build a :class:`PipelineConfig` from environment variables.

        :return: A fully populated configuration instance.
        """
        logger.debug("Loading pipeline settings from environment variables.")
        return cls(
            # Probably remove these
            data_dir=os.getenv("DATA_DIR", "data"),
            config_dir=os.getenv("CONFIG_DIR", "config"),

            collection_name=os.getenv("QDRANT_COLLECTION_NAME", "chatbot-collection"),
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            dense_model_name=os.getenv("DENSE_MODEL_NAME", "jinaai/jina-embeddings-v3"),
            sparse_model_name=os.getenv("SPARSE_MODEL_NAME", "Qdrant/bm25"),
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "9001")),
            mcp_server_name=os.getenv("MCP_SERVER_NAME", "HSNR-FB08-MCP"),
        )
    
config = PipelineConfig.from_env()
logger.debug(
    "Loaded configuration: collection=%s, qdrant_url=%s, dense_model=%s, sparse_model=%s, host=%s, port=%s",
    config.collection_name,
    config.qdrant_url,
    config.dense_model_name,
    config.sparse_model_name,
    config.host,
    config.port,
)
mcp = FastMCP(config.mcp_server_name)
logger.debug("Created FastMCP instance with server name '%s'.", config.mcp_server_name)

qdrant_service = QdrantService(
    collection_name=config.collection_name,
    qdrant_url=config.qdrant_url,
    embed_svc=EmbeddingService(
        dense_model_name=config.dense_model_name,
        sparse_model_name=config.sparse_model_name,
    ),
)
logger.debug("Initialized Qdrant service for collection '%s'.", config.collection_name)

register_search_tools(mcp=mcp, qdrant_svc=qdrant_service)
logger.debug("Registered search tools on the MCP server.")
register_static_info_tools(mcp=mcp)
logger.debug("Registered static info tools on the MCP server.")

register_file_access_tools(mcp=mcp, data_dir=config.data_dir, qdrant_svc=qdrant_service)



if __name__ == "__main__":
    logger.debug("Starting MCP server on %s:%s.", config.host, config.port)
    mcp.run(transport="sse", host=config.host, port=config.port)

        