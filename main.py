from google import genai

from src.rag.chunker import compute_breakpoints, compute_distances, embed_sentences, flatten_pages_to_sentences, group_sentences_into_chunks


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from src.rag.pdf_parser import parse_pdf

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    pages = parse_pdf("data/demo_docs/DSA.pdf")
    sentences = flatten_pages_to_sentences(pages)

    sample = sentences[:60]  # tăng dần khi đã tin tưởng logic chạy đúng
    sample = embed_sentences(sample, client)
    distances = compute_distances(sample)
    breakpoints = compute_breakpoints(sample, distances, percentile=95)
    chunks = group_sentences_into_chunks(sample, breakpoints, min_sentences=2, max_chars=800)

    print(f"Số câu: {len(sample)} -> Số chunk: {len(chunks)}\n")
    for c in chunks:
        print(f"--- Chunk {c.chunk_id} (p.{c.page_start}-{c.page_end}, {c.sentence_count} câu) ---")
        print(c.text[:200])
        print()