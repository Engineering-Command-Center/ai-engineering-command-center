"""
PromptBuilder — assembles the system + user prompt sent to Gemini.

Design principles:
- The model is instructed to answer ONLY from the supplied context.
- Each context block is labelled with its source (repo, file, lines) so the
  model can cite it and so the answer remains traceable.
- If no relevant context is available the model is instructed to say so rather
  than hallucinate.
- A hard token budget is enforced by truncating context blocks from the bottom
  (lowest-scoring chunks) when the total character count exceeds the limit.
"""

from __future__ import annotations

from app.services.retriever import RetrievedChunk

# Conservative character ceiling for the entire context section.
# Gemini 2.5 Flash supports a 1M-token context window, but we keep prompts
# focused — wide context with low-relevance chunks hurts answer quality.
_CONTEXT_CHAR_BUDGET = 24_000
_NO_CONTEXT_MARKER = "(No relevant context found in the indexed codebase.)"

# Maximum characters shown per chunk in the prompt (avoids one huge chunk
# dominating the context while others are squeezed out).
_MAX_CHARS_PER_CHUNK = 3_000

SYSTEM_PROMPT = """\
You are an expert engineering assistant with access to your organisation's \
source code, configuration, and documentation.

Rules you MUST follow:
1. Answer ONLY from the context blocks supplied below — do not use outside knowledge.
2. If the context does not contain enough information to answer, say exactly:
   "I could not find relevant information in the indexed codebase."
3. Be precise and technical. Quote relevant code snippets where helpful.
4. At the end of your answer cite the sources you used in this exact format:
   Sources: <repo>/<file_path>:<start_line>-<end_line>
   (one source per line, only sources you actually used)
"""


class PromptBuilder:
    """
    Builds the full prompt string from a question and a ranked list of
    retrieved chunks.  Chunks are ordered by descending score (most relevant
    first) and trimmed to fit inside `_CONTEXT_CHAR_BUDGET`.
    """

    def build(self, question: str, chunks: list[RetrievedChunk]) -> str:
        context_section = self._build_context(chunks)
        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"{'=' * 60}\n"
            f"CONTEXT\n"
            f"{'=' * 60}\n"
            f"{context_section}\n"
            f"{'=' * 60}\n\n"
            f"QUESTION\n{question}"
        )

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return _NO_CONTEXT_MARKER

        # Highest-score first — retriever already returns them ranked but be explicit.
        ranked = sorted(chunks, key=lambda c: c.score, reverse=True)

        blocks: list[str] = []
        total_chars = 0

        for i, chunk in enumerate(ranked, start=1):
            text = chunk.text
            if len(text) > _MAX_CHARS_PER_CHUNK:
                text = text[:_MAX_CHARS_PER_CHUNK] + "\n… [truncated]"

            header = (
                f"[{i}] {chunk.repo}/{chunk.file_path} "
                f"(lines {chunk.start_line}–{chunk.end_line}, "
                f"score={chunk.score:.4f})"
            )
            block = f"{header}\n```{chunk.language}\n{text}\n```"
            block_chars = len(block)

            if total_chars + block_chars > _CONTEXT_CHAR_BUDGET:
                # Budget exhausted — remaining chunks (lower score) are dropped.
                break

            blocks.append(block)
            total_chars += block_chars

        return "\n\n".join(blocks)
