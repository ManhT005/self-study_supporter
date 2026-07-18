store = VectorStore()

    # existing_ids = store.get_existing_ids(
    #     [c.chunk_id for c in chunks]
    # )

    # new_chunks = [
    #     c
    #     for c in chunks
    #     if c.chunk_id not in existing_ids
    # ]

    # if new_chunks:
    #     vectors = embed_chunks(new_chunks, client)
    #     store.add_chunks(new_chunks, vectors)

    # def embed_query_fn(query: str) -> list[float]:
    #     result = client.models.embed_content(
    #         model="gemini-embedding-001",
    #         contents=query,
    #         config=EmbedContentConfig(
    #             task_type="RETRIEVAL_QUERY",   # khác RETRIEVAL_DOCUMENT lúc lưu chunk
    #             output_dimensionality=768,
    #         ),
    #     )
    #     return result.embeddings[0].values

    # bm25_index = BM25Index(chunks)  # dùng lại list `chunks` đã tạo ở bước chunking

    # query = "Dữ liệu là gì?"
    # top_chunks = hybrid_search(query, store, bm25_index, embed_query_fn, top_k=3)


    # for c in top_chunks:
    #     print(f"--- {c.chunk_id} (p.{c.page_start}-{c.page_end}) ---")
    #     print(c.text[:200])
    #     print()