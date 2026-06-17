def chunk_text(text, chunk_size=4000, overlap=400):
    """
    Split text into overlapping chunks.
    Tries to break at sentence/paragraph boundaries for cleaner chunks.
    """
    chunks = []
    if not text:
        return chunks

    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        if end < text_len:
            # Try to break at paragraph boundary first
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break != -1:
                end = para_break + 2
            else:
                # Fall back to sentence boundary
                sent_break = text.rfind(". ", start + chunk_size // 2, end)
                if sent_break != -1:
                    end = sent_break + 2

        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)

        start = end - overlap
        if start >= text_len:
            break

    return chunks
