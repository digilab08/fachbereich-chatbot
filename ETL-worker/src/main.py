"""Entry point for the ETL worker.

This module orchestrates the full extract-transform-load pipeline that
ingests Moodle course materials, converts them into searchable chunks and
stores them in a Qdrant collection for retrieval by the chatbot.

The pipeline is divided into four phases:

1. **Extract** - Discover relevant files from the local Moodle mirror based on
   the extraction configuration.
2. **Diff** - Compare the discovered files against the already processed data
   to determine new, changed and removed files.
3. **Cleanup** - Remove processed artifacts and Qdrant points for files that no
   longer exist in the source.
4. **Transform & Load** - Convert new and changed files into chunks, embed
   them and upload the results to Qdrant.
"""

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from extract import moodle_extract_relevant_files
from load import QdrantCollection
from transform import DiffFileStates, FileProcessor, cleanup_removed_files
from utils import ProgressLogger, get_csv_as_dict_list, get_logger

load_dotenv()
logger = get_logger(__name__)


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
    """

    extraction_config_path: str
    data_path: str
    processed_folder_path: str
    moodle_url: str
    collection_name: str
    qdrant_url: str

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Build a :class:`PipelineConfig` from environment variables.

        :return: A fully populated configuration instance.
        """
        return cls(
            extraction_config_path=os.getenv("EXTRACTION_CONFIG_PATH", "extraction_config.csv"),
            data_path=os.getenv("DATA_PATH", "data"),
            processed_folder_path=os.getenv("PROCESSED_FOLDER_PATH", "processed-data"),
            moodle_url=os.getenv("MOODLE_URL", "https://moodle.hsnr.de"),
            collection_name=os.getenv("QDRANT_COLLECTION_NAME", "chatbot-collection"),
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        )


def extract_relevant_files(config: PipelineConfig) -> list[dict[str, Any]]:
    """Run the extraction phase and return the relevant files.

    :param config: The active pipeline configuration.
    :return: List of relevant file descriptors discovered in the data mirror.
    """
    logger.debug("Starting extraction phase")
    extraction_config = get_csv_as_dict_list(config.extraction_config_path)
    relevant_files = list(
        moodle_extract_relevant_files(
            data_path=config.data_path,
            extraction_config=extraction_config,
            moodle_url=config.moodle_url,
        )
    )
    logger.info("Relevant files: %d", len(relevant_files))
    return relevant_files


def diff_file_states(
    relevant_files: list[dict[str, Any]],
    config: PipelineConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Compare the current relevant files against the processed data.

    :param relevant_files: Files discovered during the extraction phase.
    :param config: The active pipeline configuration.
    :return: A tuple of ``(new_files, removed_files, changed_files)``.
    """
    logger.debug("Starting diffing of file states")
    diff = DiffFileStates(relevant_files, config.processed_folder_path)
    new_files = diff.get_new_files()
    removed_files = diff.get_removed_files()
    changed_files = diff.get_changed_files()

    logger.info("New files: %d", len(new_files))
    logger.info("Removed files: %d", len(removed_files))
    logger.info("Changed files: %d", len(changed_files))
    return new_files, removed_files, changed_files


def cleanup_removed(
    removed_files: list[dict[str, Any]],
    config: PipelineConfig,
    qdrant_collection: QdrantCollection,
) -> None:
    """Remove artifacts of files that no longer exist in the source.

    Deletes the processed markdown files from disk and the corresponding
    points from the Qdrant collection.

    :param removed_files: File descriptors that have been removed since the
        last run.
    :param config: The active pipeline configuration.
    :param qdrant_collection: The Qdrant collection to delete points from.
    """
    logger.debug("Cleaning up removed files from processed data folder and Qdrant collection")
    sources_to_remove = [file["source"] for file in removed_files]
    cleanup_removed_files(
        processed_data_path=config.processed_folder_path,
        removed_file_paths=sources_to_remove,
    )
    qdrant_collection.delete_by_source(sources_to_remove)


def process_and_upload(
    files_to_process: list[dict[str, Any]],
    file_processor: FileProcessor,
    qdrant_collection: QdrantCollection,
) -> None:
    """Convert, embed and upload the given files to Qdrant.

    Each file is processed independently. A failure for one file is logged
    but does not abort the remaining files.

    :param files_to_process: New and changed files to process.
    :param file_processor: Processor used to convert and chunk files.
    :param qdrant_collection: The Qdrant collection to upload chunks to.
    """
    logger.debug("Processing and uploading new and changed files to Qdrant collection")
    progress = ProgressLogger(
        task_name="Process and Upload Files",
        total_steps=len(files_to_process),
        logger=logger,
    )
    progress.start()

    for file_to_process in files_to_process:
        logger.debug("Processing file: %s", file_to_process["source"])
        try:
            processed_file_chunks = file_processor.process_file(file_to_process)
            logger.debug("%s - %d chunks", file_to_process["source"], len(processed_file_chunks))
            if not processed_file_chunks:
                continue
            qdrant_collection.upload_chunks(processed_file_chunks)
        except Exception:
            logger.exception(
                "Failed to process and upload file: %s",
                file_to_process.get("source", file_to_process),
            )
        finally:
            progress.step()

    progress.finish()


def main() -> None:
    """Run the full ETL pipeline end to end.

    The phases are executed in order: extract, diff, cleanup and finally
    transform & load. Errors in individual file processing are isolated, but
    errors in the orchestration phases will propagate and abort the run.
    """
    config = PipelineConfig.from_env()

    logger.debug("Starting ETL process")

    relevant_files = extract_relevant_files(config)

    new_files, removed_files, changed_files = diff_file_states(relevant_files, config)

    files_to_process = new_files + changed_files
    logger.debug("Files to process: %d", len(files_to_process))

    file_processor = FileProcessor(output_folder_path=config.processed_folder_path)
    qdrant_collection = QdrantCollection(
        collection_name=config.collection_name,
        qdrant_url=config.qdrant_url,
    )
    if not qdrant_collection.test_connection():
        logger.error("Failed to connect to Qdrant at %s", config.qdrant_url)
        return

    cleanup_removed(removed_files, config, qdrant_collection)
    process_and_upload(files_to_process, file_processor, qdrant_collection)


if __name__ == "__main__":
    main()

