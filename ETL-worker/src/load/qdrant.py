import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)


class QdrantCollection:
    """
    Uploads pre-embedded text chunks into a Qdrant collection using hybrid
    search (dense and sparse vectors).

    The actual embedding generation happens in the transform step
    (``transform.embed.Embedder``). This class only persists the already
    computed vectors together with the chunk payload.

    :param collection_name: The name of the Qdrant collection to upload the chunks to.
    :param qdrant_url: The URL of the Qdrant instance. Defaults to ``"http://localhost:6333"``.
    """

    def __init__(
        self,
        collection_name: str,
        qdrant_url: str = "http://localhost:6333",
    ) -> None:
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

    def upload_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Main entry point to upload a list of pre-embedded chunks to Qdrant.

        :param chunks: A list of dictionaries containing chunk metadata, text
            and the precomputed ``dense_vector``, ``sparse_indices`` and
            ``sparse_values`` keys.
        """
        if not chunks:
            return

        points = self._build_points(chunks)
        self._ensure_collection_exists(self.collection_name, points[0])
        self._upload_to_qdrant(points)

    def _build_points(self, chunks: List[Dict[str, Any]]) -> List[PointStruct]:
        """
        Structures pre-embedded chunks as Qdrant PointStructs.

        :param chunks: The list of chunk dictionaries with precomputed vectors.
        :return: A list of Qdrant points ready for upload.
        """
        points = []
        for chunk in chunks:
            payload = {
                key: value
                for key, value in chunk.items()
                if key not in {"dense_vector", "sparse_indices", "sparse_values"}
            }

            vectors = {
                "dense": chunk["dense_vector"],
                "sparse": SparseVector(
                    indices=chunk["sparse_indices"],
                    values=chunk["sparse_values"],
                ),
            }

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors,
                payload=payload,
            )
            points.append(point)

        return points

    def _ensure_collection_exists(self, collection_name: str, sample_point: PointStruct) -> None:
        """
        Checks if the specified collection exists and creates it with hybrid
        vector configurations if not.

        :param collection_name: The name of the collection to check or create.
        :param sample_point: A sample point to extract the dense vector dimension dynamically.
        """
        if not self.client.collection_exists(collection_name):
            dense_vector_size = len(sample_point.vector["dense"])

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=dense_vector_size,
                        distance=Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(),
                },
            )

    def _upload_to_qdrant(self, points: List[PointStruct]) -> None:
        """
        Uploads the fully structured points to the specified Qdrant collection.

        :param points: The points containing vectors and payloads.
        """
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def delete_by_source(self, collection_name: str, source: str | List[str]) -> None:
        """
        Deletes all document chunks in the specified collection that match the
        given source or list of sources.

        :param collection_name: The name of the Qdrant collection.
        :param source: A single source identifier or a list of source identifiers to match for deletion.
        """
        if isinstance(source, str):
            match_condition = MatchValue(value=source)
        else:
            match_condition = MatchAny(any=source)

        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="source",
                    match=match_condition,
                )
            ]
        )

        self.client.delete(
            collection_name=collection_name,
            points_selector=delete_filter,
        )