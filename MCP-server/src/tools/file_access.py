import os
import re
from pathlib import Path
from fastmcp import FastMCP
from services.qdrant_svc import QdrantService
from utils import get_all_headings, get_section, improve_url

def register_file_access_tools(mcp: FastMCP, data_dir: str, qdrant_svc: QdrantService) -> None:
    """
    Register file access tools on the given FastMCP server instance.

    :param mcp: The FastMCP server instance.
    :param data_dir: The directory where file data is stored.
    :param qdrant_svc: The Qdrant service used for metadata search.

    """

    BASE_DIR = Path(data_dir).resolve()

    def get_safe_path(requested_path: str) -> Path:
        """Validate the path and prevent path traversal."""
        target_path = (BASE_DIR / requested_path).resolve()

        if not target_path.is_relative_to(BASE_DIR):
            raise PermissionError("Security violation: access to paths outside data_dir is forbidden.")

        return target_path

    def get_md_path(requested_path: str) -> Path:
        """Append '.md' if missing and return the validated path."""
        requested_path_obj = BASE_DIR / requested_path
        if not requested_path_obj.is_file():
            requested_path += '.md'
        return get_safe_path(requested_path)

    @mcp.tool()
    async def list_directory(path: str) -> str:
        """
        Lists the contents of the specified relative directory path.

        :param path: The relative path of the directory to list. (e.g., "moodle/Infos")
        :return: A formatted string containing the directory contents with their sizes.
        """
        try:
            safe_path = get_safe_path(path)
            if not safe_path.exists() or not safe_path.is_dir():
                return f"Error: directory '{path}' does not exist or is not a directory."

            items = []
            for item in safe_path.iterdir():
                if item.is_dir():
                    items.append(f"[DIR]  {item.name}")
                else:
                    size_kb = item.stat().st_size / 1024
                    items.append(f"[FILE] {item.name} ({size_kb:.2f} KB)")
            
            if not items:
                return "The directory is empty."
            return "\n".join(sorted(items))
        except Exception as e:
            return f"Access error: {str(e)}"

    @mcp.tool()
    async def read_file(file_path: str, specific_heading: str | None = None) -> str:
        """
        Retrieves the content or a specific section of the specified file.
        If the file exceeds 10 KB, you should provide a `specific_heading`, otherwise the request will respond with all headers 
        in the file, and the request can be repeated with a specified heading.
        
        :param file_path: The relative path of the file (e.g. "moodle/Infos/Prüfungsordnung.pdf").
        :param specific_heading: The EXACT text of the markdown heading (without the '#' symbols) to extract only that section.
        :return: The file content, the specific section or the list of headings.
        """
        try:
            safe_path = get_md_path(file_path)

            try:
                # Check if the file exists in Qdrant
                qdrant_results = await qdrant_svc.search_payload(
                    filters={"file_path": file_path},
                    limit=1
                )
                if not qdrant_results:
                    url = qdrant_results[0].payload.get("url", "")
            except Exception as e:
                url = ""
            url = improve_url(url, None)
            url_param = f" url='{url}'" if url else ""
            
            if not safe_path.exists() or not safe_path.is_file():
                return f"Error: File '{file_path}' does not exist."

            if(specific_heading):
                section_content = get_section(safe_path, specific_heading)
                if section_content is None:
                    return f"Error: heading '{specific_heading}' was not found in the file."
                return f"<section_content{url_param}>{section_content}</section_content>"

            MAX_FILE_SIZE_BYTES = 10 * 1024 
            if safe_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                result_lines = [f"{heading['level'] * '#'} {heading['title']}" for heading in get_all_headings(safe_path)]
                return "The file is too large to display in full. Please specify one of the following headings:" + "\n".join(result_lines)

            return f"<file_content{url_param}>{safe_path.read_text(encoding='utf-8')}</file_content>"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    # TODO: Add file search by name mcp-tool