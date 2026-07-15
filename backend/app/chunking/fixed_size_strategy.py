from app.chunking.base import ChunkStrategy


class FixedSizeChunkStrategy(ChunkStrategy):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if self.chunk_size <= self.chunk_overlap:
            raise ValueError("chunk_size must be strictly greater than chunk_overlap.")

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk_text = text[start:end]
            if chunk_text.strip():  # Only add non-empty chunks
                chunks.append(chunk_text)
            start += (self.chunk_size - self.chunk_overlap)

        return chunks
