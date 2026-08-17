from typing import Any, Dict, List

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
    """

    def __init__(
        self,
        dense_model: str = "jinaai/jina-embeddings-v3",
        sparse_model: str = "Qdrant/bm25",
    ) -> None:
        self.dense_embedder = TextEmbedding(model_name=dense_model)
        self.sparse_embedder = SparseTextEmbedding(model_name=sparse_model)

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Generate dense and sparse embeddings for the given chunks and attach them
        in-place as ``dense_vector``, ``sparse_indices`` and ``sparse_values``.

        Storing the sparse vector components as plain lists keeps the transform
        step independent of any specific vector database client.

        :param chunks: List of chunk dictionaries. Each chunk must contain
            ``dense_embedding_text`` and ``sparse_embedding_text`` keys.
        """
        if not chunks:
            return

        dense_texts = [chunk["dense_embedding_text"] for chunk in chunks]
        sparse_texts = [chunk["sparse_embedding_text"] for chunk in chunks]

        # fastembed returns generators, materialise them once here
        dense_embeddings = list(self.dense_embedder.embed(dense_texts))
        sparse_embeddings = list(self.sparse_embedder.embed(sparse_texts))

        for idx, chunk in enumerate(chunks):
            dense_vec = dense_embeddings[idx]
            sparse_vec = sparse_embeddings[idx]

            chunk["dense_vector"] = dense_vec.tolist()
            chunk["sparse_indices"] = sparse_vec.indices.tolist()
            chunk["sparse_values"] = sparse_vec.values.tolist()
