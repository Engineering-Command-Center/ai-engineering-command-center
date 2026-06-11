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

from app.schemas.rag import ConversationTurn
from app.services.retriever import RetrievedChunk

# Conservative character ceiling for the entire context section.
# Gemini 2.5 Flash supports a 1M-token context window, but we keep prompts
# focused — wide context with low-relevance chunks hurts answer quality.
_CONTEXT_CHAR_BUDGET = 24_000
_NO_CONTEXT_MARKER = "(No relevant context found in the indexed codebase.)"

# Maximum characters shown per chunk in the prompt (avoids one huge chunk
# dominating the context while others are squeezed out).
_MAX_CHARS_PER_CHUNK = 3_000

# How many prior turns to include (each turn = 1 user + 1 assistant message).
# Keep this low to avoid bloating the prompt; the most recent turns matter most.
_MAX_HISTORY_TURNS = 5

SYSTEM_PROMPT = """\
You are an expert engineering assistant for a tech company. You have access to \
the organisation's source code, configuration, and documentation — but you are \
also a knowledgeable senior engineer who can help with general engineering tasks.

Rules you MUST follow:
1. If relevant context blocks are provided below, prioritise them in your answer \
and cite the sources you used.
2. If no relevant context is found in the codebase BUT the question is a general \
engineering or technical question (writing JDs, explaining concepts, architecture \
advice, best practices, etc.) — answer using your own expert knowledge. Do NOT \
refuse these questions.
3. Only say "I could not find relevant information" if the question is specifically \
asking about this codebase and no context was found (e.g. "how does our auth work?" \
with no matching code).
4. Be precise and technical. Quote relevant code snippets where helpful.
5. Maintain continuity with the conversation history provided — refer back to \
previous questions and answers when relevant.
6. When you use codebase context, cite sources at the end in this format:
   Sources: <repo>/<file_path>:<start_line>-<end_line>
   (one source per line, only sources you actually used)
"""


class PromptBuilder:
    """
    Builds the full prompt string from a question, conversation history,
    and a ranked list of retrieved chunks.
    """

    def build(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        history: list[ConversationTurn] | None = None,
    ) -> str:
        context_section = self._build_context(chunks)
        history_section = self._build_history(history or [])
        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"{'=' * 60}\n"
            f"CONTEXT\n"
            f"{'=' * 60}\n"
            f"{context_section}\n"
            f"{'=' * 60}\n"
            f"{history_section}"
            f"QUESTION\n{question}"
        )

    def _build_history(self, history: list[ConversationTurn]) -> str:
        if not history:
            return ""
        # Keep only the most recent N turns (pairs of user+assistant)
        # A "turn" here means individual messages, so take last 2*N messages
        recent = history[-(2 * _MAX_HISTORY_TURNS):]
        lines = ["CONVERSATION HISTORY\n" + "=" * 60]
        for turn in recent:
            prefix = "User" if turn.role == "user" else "Assistant"
            # Truncate long assistant answers to avoid bloating prompt
            content = turn.content if len(turn.content) <= 800 else turn.content[:800] + "… [truncated]"
            lines.append(f"{prefix}: {content}")
        lines.append("=" * 60 + "\n\n")
        return "\n".join(lines) + "\n"

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
