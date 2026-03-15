"""
Text chunking module — splits raw text into overlapping semantic chunks.
"""
from config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, source_name: str) -> list[dict]:
    """
    Split *text* into overlapping chunks and return a list of dicts:
        {"text": str, "chunk_id": str, "source": str}
    """
    chunks: list[dict] = []
    separators = ["\n\n", "\n", ". ", " "]
    raw_chunks = _recursive_split(text, separators, CHUNK_SIZE)

    for idx, chunk in enumerate(raw_chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        chunks.append({
            "text": chunk,
            "chunk_id": f"{source_name}_chunk_{idx}",
            "source": source_name,
        })

    return chunks


def _recursive_split(text: str, separators: list[str], max_len: int) -> list[str]:
    """
    Recursively split text using the first applicable separator,
    merging small pieces back together with overlap.
    """
    if len(text) <= max_len:
        return [text]

    # Find the best separator present in the text
    separator = ""
    for sep in separators:
        if sep in text:
            separator = sep
            break

    if not separator:
        # Hard split if no separator works
        parts = []
        for i in range(0, len(text), max_len - CHUNK_OVERLAP):
            parts.append(text[i : i + max_len])
        return parts

    splits = text.split(separator)
    merged: list[str] = []
    current = ""

    for piece in splits:
        candidate = (current + separator + piece).strip() if current else piece.strip()
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                merged.append(current)
            # If the piece itself is too long, recurse with next separator
            if len(piece) > max_len:
                remaining_seps = separators[separators.index(separator) + 1 :] if separator in separators else []
                if remaining_seps:
                    merged.extend(_recursive_split(piece, remaining_seps, max_len))
                else:
                    for i in range(0, len(piece), max_len - CHUNK_OVERLAP):
                        merged.append(piece[i : i + max_len])
                current = ""
            else:
                current = piece

    if current:
        merged.append(current)

    # Add overlap between consecutive chunks
    overlapped: list[str] = []
    for i, chunk in enumerate(merged):
        if i > 0 and CHUNK_OVERLAP > 0:
            prev = merged[i - 1]
            overlap_text = prev[-CHUNK_OVERLAP:]
            chunk = overlap_text + chunk
        overlapped.append(chunk)

    return overlapped
