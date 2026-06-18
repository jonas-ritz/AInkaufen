"""Daily AI news and learning digest via Claude API with web search."""

import logging
import re
import sys

import anthropic

from .config import DigestConfig
from .notifier import send_email

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt (user-defined — do not change without user approval)
# ---------------------------------------------------------------------------

_DIGEST_PROMPT = """\
Erstelle ein tägliches KI-Nachrichten- und Lern-Digest für einen Softwareentwickler.

Sammle die neuesten KI-Nachrichten der letzten 24 Stunden – einschließlich technischer \
Durchbrüche, Modellveröffentlichungen, Branchenentwicklungen und Forschungsarbeiten. \
Halte die Balance zwischen technischer Tiefe und gesellschaftlicher Relevanz. Es sollte \
nicht zu tiefgehend sein, ein hohes Niveau (Überblick) genügt. Dabei soll es nicht im \
Detail um Hardware gehen: es soll um die Software gehen, gesellschaftliche und \
geschäftliche Entwicklungen.

Fasse 3–5 wichtige Meldungen in jeweils 2–3 Sätzen zusammen, geschrieben für einen \
Entwickler, der beruflich auf dem Laufenden und auf dem Arbeitsmarkt wettbewerbsfähig \
bleiben möchte. Aber eher die großen, wesentlichen Dinge.

Wähle ein wichtiges KI-Konzept oder eine Technik aus (z. B. Attention-Mechanismen, \
Retrieval-Augmented Generation, Quantisierung, Constitutional AI) und erkläre es klar \
und verständlich in 150–200 Wörtern – verwende Analogien und Beispiele, die für einen \
Softwareentwickler nachvollziehbar sind. Beginne mit einigen Grundkonzepten, es darf \
auch mathematisch sein. Das Konzept soll jeden Tag ein anderes sein.

Halte die Gesamtlänge bei etwa 500 Wörtern.

Formatiere das Ganze als gut lesbares Digest mit einem Abschnitt "News" und \
anschließend einem Abschnitt "Concept of the Day" (Konzept des Tages). Falls keine \
bedeutenden Nachrichten verfügbar sind, vermerke dies kurz und füge dennoch die \
Konzepterklärung hinzu.\
"""

# ---------------------------------------------------------------------------
# Markdown → HTML conversion (handles what Claude typically produces)
# ---------------------------------------------------------------------------

def _inline_bold(text: str) -> str:
    """Replace **text** with <strong>text</strong>."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def _markdown_to_html(text: str) -> str:
    """Convert Markdown (headers, bold, bullet lists, paragraphs) to HTML."""
    lines = text.splitlines()
    html: list[str] = []
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            html.append("</ul>")
            in_ul = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("### "):
            close_ul()
            html.append(f"<h3>{_inline_bold(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_ul()
            html.append(f"<h2>{_inline_bold(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            close_ul()
            html.append(f"<h1>{_inline_bold(stripped[2:])}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{_inline_bold(stripped[2:])}</li>")
        elif stripped == "":
            close_ul()
            # Blank lines between paragraphs — let block elements carry spacing
        else:
            close_ul()
            html.append(f"<p>{_inline_bold(stripped)}</p>")

    close_ul()
    return "\n".join(html)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def generate_digest(config: DigestConfig) -> str:
    """
    Call Claude with web search to generate the daily AI digest.

    Returns the final text (Markdown) from the model.
    Claude handles the web-search tool loop server-side; we only need to
    re-send the request if the server returns ``pause_turn``.

    Raises ``anthropic.APIError`` on API failures.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    messages: list[dict[str, object]] = [
        {"role": "user", "content": _DIGEST_PROMPT}
    ]
    tools = [{"type": "web_search_20260209", "name": "web_search"}]

    response: anthropic.types.Message | None = None
    MAX_CONTINUATIONS = 3

    for attempt in range(MAX_CONTINUATIONS):
        logger.info("Digest: API call attempt %d/%d", attempt + 1, MAX_CONTINUATIONS)
        with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=4096,
            tools=tools,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            response = stream.get_final_message()

        stop_reason = response.stop_reason
        logger.info("Digest: stop_reason=%s", stop_reason)

        if stop_reason in ("end_turn", "stop_sequence"):
            break
        elif stop_reason == "pause_turn":
            # Server-side tool loop hit its iteration limit; extend it
            messages.append(
                {"role": "assistant", "content": response.content}  # type: ignore[arg-type]
            )
        else:
            logger.warning("Digest: unexpected stop_reason=%s — treating as done", stop_reason)
            break

    if response is None:
        raise RuntimeError("Claude API returned no response")

    # Log all content block types to help debug unexpected responses
    block_types = [getattr(b, "type", type(b).__name__) for b in response.content]
    logger.info("Digest: response content block types: %s", block_types)

    # Claude emits intermediate text blocks during the web-search loop
    # ("Ich suche jetzt nach...", "Ich habe folgendes gefunden...").
    # The actual digest always appears after the last tool-result block.
    # Find the index of the last non-text block and take only what follows.
    last_tool_idx = -1
    for i, block in enumerate(response.content):
        if getattr(block, "type", None) != "text":
            last_tool_idx = i

    final_blocks = [
        b.text  # type: ignore[attr-defined]
        for b in response.content[last_tool_idx + 1:]
        if getattr(b, "type", None) == "text"
    ]
    text = "\n\n".join(block.strip() for block in final_blocks if block.strip())

    if not text:
        logger.error(
            "Digest: no final text block found after last tool result. Block types: %s",
            block_types,
        )
    else:
        logger.info(
            "Digest: extracted %d final text block(s), %d chars",
            len(final_blocks), len(text),
        )
    return text.strip()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the daily AI digest and send it by email."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Starting daily AI digest")

    try:
        config = DigestConfig.from_env()
    except OSError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    try:
        digest_text = generate_digest(config)
    except anthropic.APIError as exc:
        logger.error("Claude API error: %s", exc)
        sys.exit(1)

    if not digest_text:
        logger.error("Empty digest returned by Claude — aborting")
        sys.exit(1)

    digest_html = _markdown_to_html(digest_text)

    logger.info("Sending digest email to %s", config.email_to)
    if not send_email(digest_html, config, subject="🤖 Dein tägliches KI-Digest"):
        logger.error("Failed to send digest email")
        sys.exit(1)

    logger.info("Digest email sent successfully")


if __name__ == "__main__":
    main()
