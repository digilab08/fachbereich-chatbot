import asyncio
from typing import List, Tuple, Any
from fastembed import TextEmbedding, SparseTextEmbedding
import numpy as np

class EmbeddingService:
    def __init__(
        self, 
        dense_model_name: str = "jinaai/jina-embeddings-v3", 
        sparse_model_name: str = "Qdrant/bm25"
    ) -> None:
        """
        Initialize the embedding models. Note that this downloads the models 
        if they are not already cached locally.

        :param dense_model_name: Identifier for the dense model.
        :param sparse_model_name: Identifier for the sparse model.
        """
        self.dense_model = TextEmbedding(model_name=dense_model_name)
        self.sparse_model = SparseTextEmbedding(model_name=sparse_model_name)

    async def embed_query(self, query_text: str) -> Tuple[np.ndarray, Any]:
        """
        Asynchronously generate both dense and sparse embeddings for a single query.
        
        Runs the synchronous FastEmbed generation in a separate thread.
        
        :param query_text: The search query text provided by the user.
        :return: A tuple containing the dense vector (numpy array) and the sparse embedding object.
        """
        return await asyncio.to_thread(self._embed_query_sync, query_text)

    def _embed_query_sync(self, query_text: str) -> Tuple[np.ndarray, Any]:
        """
        Synchronous worker method to generate the embeddings.
        
        :param query_text: The search query text.
        :return: A tuple of (dense_vector, sparse_embedding).
        """
        # The embed method returns an iterable, so we convert it to a list and take the first item
        dense_vector = list(self.dense_model.embed([query_text]))[0]
        sparse_embedding = list(self.sparse_model.embed([query_text]))[0]
        
        return dense_vector, sparse_embedding