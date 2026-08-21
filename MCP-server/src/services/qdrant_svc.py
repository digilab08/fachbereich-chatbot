from typing import List, Optional, Any
from qdrant_client import AsyncQdrantClient, models
from .embed_svc import EmbeddingService

class QdrantService:
    def __init__(self, qdrant_url: str, collection_name: str, embed_svc: EmbeddingService) -> None:
        """
        Initialize the asynchronous Qdrant client and assign dependencies.

        :param qdrant_url: Connection URL for the Qdrant server.
        :param collection_name: Name of the target collection.
        :param embed_svc: Instance of the EmbeddingService to encode queries.
        """
        self.client = AsyncQdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        self.embed_svc = embed_svc

    async def search_hybrid(
        self, 
        query_text: str, 
        limit: int = 5, 
        target_tags: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Perform a hybrid search with optional metadata pre-filtering.
        
        If target_tags are provided (e.g., ["BWI", "FB08"]), a filter is constructed 
        so that only documents whose 'target' field matches ANY of the tags are considered.
        This filter is applied during the prefetch stage for optimal performance.
        
        :param query_text: The search query text.
        :param limit: Maximum number of search results to return. Defaults to 5.
        :param target_tags: Optional list of target strings to filter by (OR condition).
        :return: A list of retrieved Qdrant points containing payload and scores.
        """
        # Construct the metadata filter using MatchAny for an OR condition
        query_filter = None
        if target_tags:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="target",
                        match=models.MatchAny(any=target_tags)
                    )
                ]
            )

        # Generate vectors asynchronously via our EmbeddingService
        dense_vector, sparse_embedding = await self.embed_svc.embed_query(query_text)

        sparse_vector_qdrant = models.SparseVector(
            indices=sparse_embedding.indices.tolist(),
            values=sparse_embedding.values.tolist()
        )

        search_results = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector.tolist(),
                    using="dense",
                    limit=limit,
                    filter=query_filter,
                ),
                models.Prefetch(
                    query=sparse_vector_qdrant,
                    using="sparse",
                    limit=limit,
                    filter=query_filter, 
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
        )

        return search_results.points

    async def search_payload(
        self,
        filters: dict,
        limit: int = 5,
    ) -> List[Any]:
        """
        Perform a non-vector, payload-only search (scroll) with exact field matching.

        Only points whose payload matches ALL provided filter key-value pairs are
        returned. For example, filters={"target": "lol"} returns only points where
        the payload field 'target' equals "lol".

        :param filters: Dictionary of payload field -> value to match exactly (AND condition).
        :param limit: Maximum number of results to return. Defaults to 5.
        :return: A list of retrieved Qdrant points containing payload.
        """
        must_conditions = [
            models.FieldCondition(
                key=field,
                match=models.MatchValue(value=value),
            )
            for field, value in filters.items()
        ]

        query_filter = models.Filter(must=must_conditions)

        scroll_results = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        return scroll_results[0]