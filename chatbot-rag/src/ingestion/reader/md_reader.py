import logging
import re

from .base_reader import BaseReader

from .txt_reader import TextReader

logger = logging.getLogger(__name__)

class MarkdownReader(BaseReader):
    """
    Reads Markdown files and strips syntax to plain prose.
    Extracts and converts tables to row-as-sentence format.
    """

    @property
    def supported_extensions(self):
        return [".md"]

    def extract(self, file_bytes: bytes) -> str:

        if not file_bytes:
            raise ValueError("No content found in Markdown file.")
        
        text_reader = TextReader()
        raw = text_reader.extract(file_bytes)

        # Extract and convert tables to prose before stripping syntax.
        raw, table_prose = self._extract_markdown_tables(raw)

        # Strip markdown syntax.
        raw = self._strip_markdown(raw)

        # Append converted tables.
        parts = [p for p in [raw, table_prose] if p.strip()]
        content = "\n\n".join(parts)

        if not content:
            raise ValueError("No text content found in Markdown file.")

        return content

    def _extract_markdown_tables(self, text: str) -> tuple[str, str]:
        """
        Find markdown tables, convert each row to prose,
        remove them from the main text.
        Returns (text_without_tables, table_prose)
        """
        table_pattern = re.compile(
            r"(?:^|\n)"                     # start of line
            r"(\|.+\|\n"                    # header row
            r"\|[-| :]+\|\n"                # separator row
            r"(?:\|.+\|\n)+)",              # data rows
            re.MULTILINE
        )

        table_sentences: list[str] = []

        def process_table(match: re.Match) -> str:
            lines = [l for l in match.group().strip().split("\n") if l.strip()]
            # Remove separator row (---|---)
            lines = [l for l in lines if not re.match(r"^\|[-| :]+\|$", l.strip())]
            if len(lines) < 2:
                return ""

            headers = [h.strip() for h in lines[0].strip("|").split("|")]
            for row_line in lines[1:]:
                cells = [c.strip() for c in row_line.strip("|").split("|")]
                parts = [f"{h}: {c}" for h, c in zip(headers, cells) if c]
                if parts:
                    table_sentences.append(", ".join(parts) + ".")
            return "\n"

        cleaned_text = table_pattern.sub(process_table, text)
        return cleaned_text, "\n\n".join(table_sentences)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown syntax, leaving only prose."""
        # Remove fenced code blocks.
        text = re.sub(r"```[\s\S]*?```", "", text)

        # Remove inline code.
        text = re.sub(r"`[^`]+`", "", text)

        # Remove image links.
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

        # Convert reference links to plain text.
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

        # Remove HTML tags.
        text = re.sub(r"<[^>]+>", " ", text)

        # Remove ATX headings (# ## ###, etc).
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove indented code blocks (4 spaces or 1 tab).
        text = re.sub(r"(?m)^(?: {4}|\t).+$", "", text)

        # Remove bold, italic, bold-italic emphasis (all variants).
        text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)   # bold italic ***
        text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text)   # bold **
        text = re.sub(r"\*(.+?)\*", r"\1", text)         # italic *
        text = re.sub(r"_{3}(.+?)_{3}", r"\1", text)     # bold italic ___
        text = re.sub(r"_{2}(.+?)_{2}", r"\1", text)     # bold __
        text = re.sub(r"_(.+?)_", r"\1", text)           # italic _

        # Remove horizontal rules.
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        # Collapse multiple newlines.
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Collapse multiple spaces.
        text = re.sub(r" {2,}", " ", text)

        return text.strip()