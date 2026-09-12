from typing import Any, Dict, List, Optional

from fastembed import SparseTextEmbedding, TextEmbedding


class Embedder:
    """
    Generates dense and sparse embeddings for text chunks using fastembed models.

    The embeddings are attached in-place to each chunk dictionary so that the
    subsequent load step only needs to persist them.

    :param dense_model: The name of the dense embedding model.
        Defaults to ``"jinaai/jina-embeddings-v3"``.
    :param sparse_model: The name of the sparse embedding model.
        Defaults to ``"Qdrant/bm25"``.
    :param threads: The number of threads used by ONNX Runtime. Defaults to
        None (uses all available CPU threads).
    """

    def __init__(
        self,
        dense_model: str = "jinaai/jina-embeddings-v3",
        sparse_model: str = "Qdrant/bm25",
        threads: Optional[int] = None,
    ) -> None:
        self.dense_embedder = TextEmbedding(
            model_name=dense_model,
            threads=threads,
        )
        self.sparse_embedder = SparseTextEmbedding(
            model_name=sparse_model,
            threads=threads,
        )

    def embed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 32,
    ) -> None:
        """
        Generate dense and sparse embeddings for the given chunks and attach them
        in-place as ``dense_vector``, ``sparse_indices`` and ``sparse_values``.

        :param chunks: List of chunk dictionaries. Each chunk must contain
            ``dense_embedding_text`` and ``sparse_embedding_text`` keys.
        :param batch_size: The batch size processed in a single inference step.
            Defaults to ``32`` to minimize peak memory consumption.
        """
        if not chunks:
            return

        dense_texts = (chunk["dense_embedding_text"] for chunk in chunks)
        sparse_texts = (chunk["sparse_embedding_text"] for chunk in chunks)

        # Stream directly from generators to avoid buffering all vectors in RAM
        dense_embeddings = self.dense_embedder.embed(
            dense_texts,
            batch_size=batch_size,
        )
        sparse_embeddings = self.sparse_embedder.embed(
            sparse_texts,
            batch_size=batch_size,
        )

        for chunk, dense_vec, sparse_vec in zip(
            chunks, dense_embeddings, sparse_embeddings
        ):
            chunk["dense_vector"] = dense_vec.tolist()
            chunk["sparse_indices"] = sparse_vec.indices.tolist()
            chunk["sparse_values"] = sparse_vec.values.tolist()