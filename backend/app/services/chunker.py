from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB

INDEXABLE_EXTENSIONS: frozenset[str] = frozenset(
    {
        # Python ecosystem
        ".py", ".pyi", ".pyx", ".pxd",
        # JS/TS
        ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
        # Java/JVM
        ".java", ".kt", ".kts", ".scala", ".groovy", ".gvy", ".gy",
        # Mobile
        ".swift", ".dart",
        # Systems
        ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".hh",
        ".cs", ".rs", ".go", ".zig", ".nim", ".cr", ".d",
        # Scripting
        ".rb", ".rake", ".php", ".phtml", ".pl", ".pm", ".lua", ".r", ".jl",
        # Functional
        ".hs", ".lhs", ".ex", ".exs", ".erl", ".hrl", ".clj", ".cljs", ".cljc",
        ".ml", ".mli", ".fs", ".fsi", ".fsx", ".elm",
        # Shell
        ".sh", ".bash", ".zsh", ".fish", ".ksh", ".csh",
        ".ps1", ".psm1", ".psd1", ".bat", ".cmd",
        # Web
        ".html", ".htm", ".xhtml", ".css", ".scss", ".sass", ".less", ".styl",
        ".svelte", ".vue", ".astro", ".hbs", ".mustache", ".pug", ".jade",
        ".ejs", ".j2", ".jinja", ".jinja2", ".twig", ".liquid", ".erb", ".haml", ".slim", ".mjml",
        # Config/Infra
        ".json", ".jsonc", ".json5", ".yaml", ".yml", ".toml", ".ini",
        ".cfg", ".conf", ".properties", ".env", ".hcl", ".tf", ".tfvars",
        ".nix", ".mk", ".cmake", ".gradle", ".bzl",
        # Data/Query
        ".sql", ".graphql", ".gql", ".proto", ".thrift", ".avsc", ".fbs",
        ".xml", ".xsd", ".xsl", ".wsdl", ".plist", ".csv", ".tsv",
        # Docs
        ".md", ".mdx", ".markdown", ".rst", ".adoc", ".asciidoc", ".txt", ".tex",
        # Notebooks
        ".ipynb",
        # Misc
        ".diff", ".patch", ".lock", ".mod", ".sum",
    }
)

INDEXABLE_FILENAMES: frozenset[str] = frozenset(
    {
        "Dockerfile",
        "Makefile",
        "Gemfile",
        "Pipfile",
        "Procfile",
        "Brewfile",
        "Guardfile",
        "Rakefile",
        "Vagrantfile",
        "Jenkinsfile",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
        ".env.example",
    }
)

# Languages that benefit from code-style (line-based) chunking
CODE_LANGUAGES: frozenset[str] = frozenset(
    {
        "python", "javascript", "typescript", "java", "kotlin", "scala", "groovy",
        "swift", "dart", "c", "cpp", "csharp", "rust", "go", "zig", "nim",
        "crystal", "d", "ruby", "php", "perl", "lua", "r", "julia",
        "haskell", "elixir", "erlang", "clojure", "ocaml", "fsharp", "elm",
        "shell", "powershell", "batch", "html", "css", "scss", "sass", "less",
        "svelte", "vue", "astro", "handlebars", "pug", "ejs", "jinja", "liquid",
        "erb", "haml", "sql", "graphql", "protobuf", "thrift", "xml",
        "json", "yaml", "toml", "ini", "hcl", "terraform", "nix",
        "makefile", "cmake", "dockerfile", "groovydsl", "notebook",
    }
)

_EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python", ".pyi": "python", ".pyx": "python", ".pxd": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".groovy": "groovy", ".gvy": "groovy", ".gy": "groovy",
    ".swift": "swift",
    ".dart": "dart",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hxx": "cpp", ".hh": "cpp",
    ".cs": "csharp",
    ".rs": "rust",
    ".go": "go",
    ".zig": "zig",
    ".nim": "nim",
    ".cr": "crystal",
    ".d": "d",
    ".rb": "ruby", ".rake": "ruby",
    ".php": "php", ".phtml": "php",
    ".pl": "perl", ".pm": "perl",
    ".lua": "lua",
    ".r": "r",
    ".jl": "julia",
    ".hs": "haskell", ".lhs": "haskell",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang", ".hrl": "erlang",
    ".clj": "clojure", ".cljs": "clojure", ".cljc": "clojure",
    ".ml": "ocaml", ".mli": "ocaml",
    ".fs": "fsharp", ".fsi": "fsharp", ".fsx": "fsharp",
    ".elm": "elm",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "shell",
    ".ksh": "shell", ".csh": "shell",
    ".ps1": "powershell", ".psm1": "powershell", ".psd1": "powershell",
    ".bat": "batch", ".cmd": "batch",
    ".html": "html", ".htm": "html", ".xhtml": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".styl": "stylus",
    ".svelte": "svelte",
    ".vue": "vue",
    ".astro": "astro",
    ".hbs": "handlebars", ".mustache": "handlebars",
    ".pug": "pug", ".jade": "pug",
    ".ejs": "ejs",
    ".j2": "jinja", ".jinja": "jinja", ".jinja2": "jinja",
    ".twig": "twig",
    ".liquid": "liquid",
    ".erb": "erb",
    ".haml": "haml",
    ".slim": "slim",
    ".mjml": "mjml",
    ".json": "json", ".jsonc": "json", ".json5": "json",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini", ".cfg": "ini", ".conf": "ini",
    ".properties": "properties",
    ".env": "env",
    ".hcl": "hcl",
    ".tf": "terraform", ".tfvars": "terraform",
    ".nix": "nix",
    ".mk": "makefile",
    ".cmake": "cmake",
    ".gradle": "groovydsl",
    ".bzl": "starlark",
    ".sql": "sql",
    ".graphql": "graphql", ".gql": "graphql",
    ".proto": "protobuf",
    ".thrift": "thrift",
    ".avsc": "avro",
    ".fbs": "flatbuffers",
    ".xml": "xml", ".xsd": "xml", ".xsl": "xml", ".wsdl": "xml",
    ".plist": "plist",
    ".csv": "csv",
    ".tsv": "tsv",
    ".md": "markdown", ".mdx": "markdown", ".markdown": "markdown",
    ".rst": "rst",
    ".adoc": "asciidoc", ".asciidoc": "asciidoc",
    ".txt": "text",
    ".tex": "latex",
    ".ipynb": "notebook",
    ".diff": "diff", ".patch": "diff",
    ".lock": "lock",
    ".mod": "gomod",
    ".sum": "gosum",
}

_FILENAME_TO_LANGUAGE: dict[str, str] = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
    "Gemfile": "ruby",
    "Pipfile": "toml",
    "Procfile": "text",
    "Brewfile": "ruby",
    "Guardfile": "ruby",
    "Rakefile": "ruby",
    "Vagrantfile": "ruby",
    "Jenkinsfile": "groovy",
    ".gitignore": "gitignore",
    ".gitattributes": "gitattributes",
    ".editorconfig": "editorconfig",
    ".env.example": "env",
}


@dataclass
class Chunk:
    text: str
    file_path: str
    repo: str
    language: str
    file_extension: str
    chunk_index: int
    total_chunks: int
    start_line: int
    end_line: int
    char_count: int


class ChunkingService:
    def __init__(self, max_chars: int = 4000, overlap_chars: int = 200,
                 max_lines: int = 80, overlap_lines: int = 15) -> None:
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars
        self._max_lines = max_lines
        self._overlap_lines = overlap_lines

    def is_indexable(self, path: Path) -> bool:
        try:
            stat = path.stat()
        except OSError:
            return False

        if stat.st_size > MAX_FILE_SIZE_BYTES:
            return False

        name = path.name
        if name in INDEXABLE_FILENAMES:
            return True

        suffix = path.suffix.lower()
        return suffix in INDEXABLE_EXTENSIONS

    def detect_language(self, path: Path) -> str:
        name = path.name
        if name in _FILENAME_TO_LANGUAGE:
            return _FILENAME_TO_LANGUAGE[name]

        suffix = path.suffix.lower()
        return _EXTENSION_TO_LANGUAGE.get(suffix, "text")

    def chunk_file(self, path: Path, repo_root: Path, repo_name: str) -> list[Chunk]:
        try:
            content = path.read_bytes()
        except OSError as exc:
            logger.warning("chunk_file_read_error", path=str(path), error=str(exc))
            return []

        text: str | None = None
        for encoding in ("utf-8", "latin-1"):
            try:
                text = content.decode(encoding)
                break
            except (UnicodeDecodeError, ValueError):
                continue

        if text is None:
            logger.debug("chunk_file_binary_skip", path=str(path))
            return []

        language = self.detect_language(path)
        ext = path.suffix.lower()
        rel_path = str(path.relative_to(repo_root))

        if language in CODE_LANGUAGES:
            chunks = self._chunk_code(
                text, rel_path, repo_name, language, ext,
                self._max_lines, self._overlap_lines,
            )
        else:
            chunks = self._chunk_prose(
                text, rel_path, repo_name, language, ext,
                self._max_chars, self._overlap_chars,
            )

        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _chunk_code(
        self,
        content: str,
        file_path: str,
        repo: str,
        language: str,
        ext: str,
        max_lines: int,
        overlap_lines: int,
    ) -> list[Chunk]:
        lines = content.splitlines(keepends=True)
        if not lines:
            return []

        step = max(1, max_lines - overlap_lines)
        chunks: list[Chunk] = []
        chunk_index = 0
        i = 0

        while i < len(lines):
            start = i

            # For Python, snap start to nearest def/class within 5 lines before
            if language == "python" and chunk_index > 0:
                snap_start = max(0, i - 5)
                for si in range(snap_start, i + 1):
                    stripped = lines[si].lstrip()
                    if stripped.startswith("def ") or stripped.startswith("class "):
                        start = si
                        break

            end = min(start + max_lines, len(lines))
            chunk_lines = lines[start:end]
            text = "".join(chunk_lines)

            if text.strip():
                chunks.append(
                    Chunk(
                        text=text,
                        file_path=file_path,
                        repo=repo,
                        language=language,
                        file_extension=ext,
                        chunk_index=chunk_index,
                        total_chunks=0,  # set after
                        start_line=start + 1,
                        end_line=end,
                        char_count=len(text),
                    )
                )
                chunk_index += 1

            i = i + step
            if end >= len(lines):
                break

        return chunks

    def _chunk_prose(
        self,
        content: str,
        file_path: str,
        repo: str,
        language: str,
        ext: str,
        max_chars: int,
        overlap_chars: int,
    ) -> list[Chunk]:
        paragraphs = content.split("\n\n")
        if not paragraphs:
            return []

        chunks: list[Chunk] = []
        chunk_index = 0
        current_parts: list[str] = []
        current_len = 0
        current_line = 1
        start_line = 1

        lines_so_far = 1

        def _flush(parts: list[str], s_line: int, e_line: int) -> None:
            nonlocal chunk_index
            text = "\n\n".join(parts)
            if text.strip():
                chunks.append(
                    Chunk(
                        text=text,
                        file_path=file_path,
                        repo=repo,
                        language=language,
                        file_extension=ext,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        start_line=s_line,
                        end_line=e_line,
                        char_count=len(text),
                    )
                )
                chunk_index += 1

        for para in paragraphs:
            para_len = len(para)
            para_lines = para.count("\n") + 1

            if current_len + para_len + 2 > max_chars and current_parts:
                end_line = lines_so_far
                _flush(current_parts, start_line, end_line)

                # Carry-over overlap
                carry = "\n\n".join(current_parts)
                if len(carry) > overlap_chars:
                    carry = carry[-overlap_chars:]
                current_parts = [carry] if carry.strip() else []
                current_len = len(carry)
                start_line = max(1, end_line - carry.count("\n"))

            current_parts.append(para)
            current_len += para_len + 2
            lines_so_far += para_lines + 1

        if current_parts:
            _flush(current_parts, start_line, lines_so_far)

        return chunks
