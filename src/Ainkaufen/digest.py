"""Daily AI news and learning digest via Claude API with web search."""

import base64
import io
import logging
import re
import sys
from datetime import date

import anthropic
import matplotlib
matplotlib.use("Agg")  # non-interactive backend, must be set before pyplot import
import matplotlib.pyplot as plt

from .config import DigestConfig
from .notifier import send_email

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rotating concept list — one per day, cycles every len(_CONCEPTS) days
# ---------------------------------------------------------------------------

_CONCEPTS = [
    "Transformer-Architektur (wie Encoder und Decoder zusammenspielen)",
    "Self-Attention und Multi-Head-Attention",
    "Positional Encoding (wie Reihenfolge ins Modell kommt)",
    "Tokenisierung: BPE und WordPiece",
    "Next-Token-Prediction und Autoregressive Generation",
    "Temperature, Top-P und Top-K Sampling",
    "RLHF – Reinforcement Learning from Human Feedback",
    "Constitutional AI und AI-Selbstkritik",
    "Retrieval-Augmented Generation (RAG)",
    "Vektorembeddings und semantische Ähnlichkeit",
    "Finetuning vs. Pre-Training",
    "LoRA – Low-Rank Adaptation",
    "Quantisierung von Sprachmodellen",
    "Mixture of Experts (MoE)",
    "Skalierungsgesetze (Scaling Laws)",
    "Emergente Fähigkeiten großer Modelle",
    "Chain-of-Thought Prompting",
    "Prompt Injection und Jailbreaking",
    "KV-Cache und Inferenzoptimierung",
    "Flash Attention",
    "Spekulatives Dekodieren (Speculative Decoding)",
    "PEFT – Parameter-Efficient Fine-Tuning",
    "Modell-Destillation (Knowledge Distillation)",
    "Diffusionsmodelle (Stable Diffusion, DALL-E)",
    "Multimodale Modelle (Text + Bild + Audio)",
    "AI Agents und Tool Use",
    "Function Calling / Structured Outputs",
    "Multi-Agent-Systeme",
    "Kontextfenster und Long-Context-Modelle",
    "Halluzinationen und Grounding",
    "AI Safety und Alignment",
    "Reinforcement Learning Grundlagen für LLMs",
    "GRPO und moderne RL-Algorithmen für Sprachmodelle",
    "Extended Thinking / Latentes Denken in Modellen",
    "Wissensgraphen und hybride KI-Systeme",
    "Semantische Suche und Embedding-Datenbanken",
    "Sparse Attention und effiziente Transformer",
    "Residual Connections und Layer Normalization",
    "Cross-Attention (z. B. in Encoder-Decoder-Modellen)",
    "Computer Use und GUI-Agenten",
    "Prompt Caching und Kosten­optimierung bei API-Nutzung",
    "Benchmarks und Evaluierung von Sprachmodellen",
    "Wasserzeichen und Erkennung von KI-Inhalten",
    "Text-to-Speech und Speech-to-Text Modelle",
    "Reinforcement Learning aus menschlichem Feedback (detailliert: Reward Model)",
    "Instruction Following und System Prompts",
    "Sprachmodelle als Code-Generatoren (Copilot-Ära)",
    "AI in der Softwareentwicklung: Agentische Coding-Workflows",
    "Federated Learning und Datenschutz",
    "Neurales Information Retrieval",
    "Multimodale Embeddings",
    "AI-Regulierung: EU AI Act und globale Entwicklungen",
]


def _concept_of_day() -> str:
    """Pick today's concept deterministically from the rotation list."""
    return _CONCEPTS[date.today().toordinal() % len(_CONCEPTS)]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt() -> str:
    today_str = date.today().strftime("%d. %B %Y")
    concept = _concept_of_day()
    return f"""\
Heute ist der {today_str}. Erstelle ein kompaktes KI-Digest für einen Softwareentwickler.

## News (3 Meldungen, je 2 Sätze)
Suche nach den wichtigsten KI-Neuigkeiten von heute – Software, Modelle, Geschäftliches. \
Keine Hardware. Nur die wirklich relevanten Dinge.

## Konzept des Tages: {concept}
150 Wörter. Klar, präzise, mit einer Analogie für Entwickler. Darf mathematisch sein.
Formeln als LaTeX schreiben: `$...$` für Inline-Formeln (z.B. $\sigma(x) = \frac{{1}}{{1+e^{{-x}}}}$),
`$$...$$` für eigenständige Blockformeln. Kein Fließtext mit Formeln mischen — Blockformeln auf eigene Zeile.

Keine Meta-Kommentare. Direkt starten.\
"""

# ---------------------------------------------------------------------------
# LaTeX formula rendering
# ---------------------------------------------------------------------------

def _latex_to_img(latex: str, block: bool = False) -> str:
    """Render a LaTeX expression to a base64-embedded PNG <img> tag."""
    try:
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${latex}$", fontsize=13 if block else 11, color="#1a1a1a")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight",
                    pad_inches=0.06, dpi=150, transparent=True)
        plt.close(fig)
        b64 = base64.b64encode(buf.getvalue()).decode()
        style = "display:block;margin:10px auto;" if block else "vertical-align:middle;"
        return f'<img src="data:image/png;base64,{b64}" style="{style}" alt="{latex}">'
    except Exception:
        return f"<code>{latex}</code>"


def _replace_math(text: str) -> str:
    """Replace $$...$$ and $...$ with rendered formula images."""
    text = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: _latex_to_img(m.group(1).strip(), block=True),
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\$([^$\n]+?)\$",
        lambda m: _latex_to_img(m.group(1).strip(), block=False),
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Markdown → HTML conversion (handles what Claude typically produces)
# ---------------------------------------------------------------------------

def _inline_bold(text: str) -> str:
    """Replace **text** with <strong>text</strong>."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def _markdown_to_html(text: str) -> str:
    """Convert Markdown (headers, bold, bullet/numbered lists, paragraphs) to HTML."""
    text = _replace_math(text)
    lines = text.splitlines()
    html: list[str] = []
    in_ul = False
    in_ol = False

    def close_list() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            html.append("</ul>")
            in_ul = False
        if in_ol:
            html.append("</ol>")
            in_ol = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("### "):
            close_list()
            html.append(f"<h3>{_inline_bold(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_list()
            html.append(f"<h2>{_inline_bold(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            close_list()
            html.append(f"<h1>{_inline_bold(stripped[2:])}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if in_ol:
                close_list()
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{_inline_bold(stripped[2:])}</li>")
        elif re.match(r"^\d+\.\s", stripped):
            if in_ul:
                close_list()
            if not in_ol:
                html.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s", "", stripped)
            html.append(f"<li>{_inline_bold(item)}</li>")
        elif stripped == "":
            close_list()
            # Blank lines between paragraphs — let block elements carry spacing
        else:
            close_list()
            html.append(f"<p>{_inline_bold(stripped)}</p>")

    close_list()
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
        {"role": "user", "content": _build_prompt()}
    ]
    tools = [{"type": "web_search_20260209", "name": "web_search"}]

    response: anthropic.types.Message | None = None
    MAX_CONTINUATIONS = 3

    for attempt in range(MAX_CONTINUATIONS):
        logger.info("Digest: API call attempt %d/%d", attempt + 1, MAX_CONTINUATIONS)
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
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

    today = date.today().strftime("%-d. %B %Y")
    subject = f"🤖 KI-Digest – {today}"
    logger.info("Sending digest email to %s", config.email_to)
    if not send_email(digest_html, config, subject=subject):
        logger.error("Failed to send digest email")
        sys.exit(1)

    logger.info("Digest email sent successfully")


if __name__ == "__main__":
    main()
