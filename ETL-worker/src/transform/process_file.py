from pathlib import Path
from io import BytesIO
from typing import Optional, Any
import os

from transformers import AutoTokenizer
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling.datamodel.base_models import ConversionStatus, DocumentStream
from .embed import Embedder

from utils import get_logger

logger = get_logger(__name__)

class FileProcessor:
    def __init__(
        self,
        output_folder_path: str | Path,
        dense_model: str = "jinaai/jina-embeddings-v3",
        sparse_model: str = "Qdrant/bm25",
    ) -> None:
        self.output_folder_path = Path(output_folder_path)
        self.dense_model = dense_model
        self.sparse_model = sparse_model
        self.converter = DocumentConverter()
        self.tokenizer = AutoTokenizer.from_pretrained(self.dense_model)
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            max_tokens=1000,
            repeat_table_header=True,
        )
        self.embedder = Embedder(
            dense_model=self.dense_model,
            sparse_model=self.sparse_model,
        )

    def try_conversion(self, file_path: Path | str) -> Optional[Any]:
        """Try to convert a file into a Docling conversion result.

        This method reads the given file into memory and passes a BytesIO
        stream to :class:`docling.document_converter.DocumentConverter` for
        conversion. Any exception during reading or conversion is caught and
        logged to stdout, and ``None`` is returned on failure.

        :param file_path: Path to the file to convert.
        :returns: The conversion result object on success, or ``None`` on failure.
        """

        # TODO: Test if the following improves text quality for images in PDFs. 
        # from docling.pipeline.vlm_pipeline import VlmPipeline
        # converter = DocumentConverter(
        #     format_options={
        #         # InputFormat anpassen (z. B. InputFormat.IMAGE oder InputFormat.PDF)
        #         InputFormat.IMAGE: FormatOption(pipeline_cls=VlmPipeline)
        #     }
        # )
        try:
            file_path = Path(file_path)
            file_bytes = file_path.read_bytes()

            # Guarantees that buf.close() is called when the block is exited
            with BytesIO(file_bytes) as buf:
                document_stream = DocumentStream(name=file_path.name, stream=buf)
                conversion = self.converter.convert(document_stream, raises_on_error=False) 
                if conversion.status == ConversionStatus.SUCCESS:
                    return conversion
                error_msgs = "; ".join(e.error_message for e in conversion.errors)
                logger.error("Failed to convert %s: %s", file_path.name, error_msgs)
        except Exception as e:
            logger.error("Failed to convert %s: %s", file_path, e)
        return None

    def process_file(self, relevant_file: dict[str, str | Path]) -> None:
        """
            Process a file, convert it to markdown, split it into chunks, and
            build embedding payloads for each chunk.

            The method supports regular files and ``.url`` files. For ``.url`` files,
            the content is read as UTF-8 text and stored as markdown output before
            continuing with conversion.

            :param relevant_file: Metadata dictionary describing the file to process.
                Expected keys are:

                - ``file_path`` (Path): Path to the source file.
                - ``source`` (str | Path): Logical source identifier used for output path and metadata.
                - ``target`` (str): Target identifier stored in each chunk result.
                - ``url`` (str, optional): Optional URL metadata.
            :return: A list of dictionaries, one per chunk, containing source metadata,
                chunk text, heading information, dense/sparse embedding texts, optional
                URL, and extracted page number.
        """
        file_path = relevant_file["file_path"]
        file_time_stamp = file_path.stat().st_mtime

        output_path = self.output_folder_path / (str(relevant_file["source"]) + ".md")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # TODO: If .md file check if .url file with the same name exists and if so, read the .url file content and write it to the .md file before proceeding with conversion and skip the .url file processing. This is to ensure that .url files are processed correctly and their content is preserved in the markdown output.

        if file_path.is_file() and file_path.suffix.lower() == ".url":
            try:
                content = file_path.read_text(encoding="utf-8")
                output_path.write_text(content, encoding="utf-8")
                file_path = output_path
            except UnicodeDecodeError:
                return

        docling_conversion = self.try_conversion(file_path)
        if docling_conversion is None: return []
        docling_document = docling_conversion.document

        markdown_output = docling_document.export_to_markdown()
        output_path.write_text(markdown_output, encoding="utf-8")
        os.utime(output_path, (file_time_stamp, file_time_stamp))

        chunks_iter = self.chunker.chunk(dl_doc=docling_document)

        def chunk_to_dict(chunk):
            source = relevant_file["source"]
            source_path = Path(source)
            source_parents = source_path.parts[:-1] 
            filename = source_path.stem
            headings = getattr(chunk.meta, "headings", []) or []

            prefix = f"The headings are: {' > '.join(headings)}." if headings else f"Title is {source_path.name}."
            tags = f"Tags are {str(source_parents)}."
            dense_embedding_text = f"{prefix}\n{tags}\nContent: {chunk.text}\n"

            sparse_embedding_text = f"{' '.join(source_parents)} {filename} {' '.join(headings)} {chunk.text}"


            return {
                "source": source,
                "target": relevant_file["target"],
                "headings": headings,
                "text": chunk.text,
                "dense_embedding_text": dense_embedding_text,
                "sparse_embedding_text": sparse_embedding_text,
                "url": relevant_file.get("url"),
                "page_number": get_chunk_page_number(chunk),
                "timestamp": relevant_file.get("timestamp"),
            }

        result = list(map(chunk_to_dict, list(chunks_iter)))

        # Attach dense and sparse embeddings so the load step only persists them
        self.embedder.embed_chunks(result)

        return result

def get_chunk_page_number(chunk: Any) -> Optional[int]:
    """
    Extracts any available page number from a given Docling chunk.
    
    This function iterates through the document items within the chunk's
    metadata and inspects their provenance details to find a page number.
    
    :param chunk: The chunk object generated by a Docling chunker.
    :return: The first encountered page number, or None if the document has no pages.
    """
    if not hasattr(chunk, "meta") or not hasattr(chunk.meta, "doc_items"):
        return None

    for item in chunk.meta.doc_items:
        if hasattr(item, "prov"):
            for prov in item.prov:
                if hasattr(prov, "page_no") and prov.page_no is not None:
                    return prov.page_no
                    
    return None