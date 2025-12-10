import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from topic_utils import topic_file

DEFAULT_URLS_FILE = Path(__file__).with_name("result_url.txt")
DEFAULT_SUMMARY_FILE = Path(__file__).with_name("summaries.txt")
DEFAULT_TOPIC = "Answer Engine Optimization"
MAX_SENTENCES_PER_SUMMARY = 6
WORDS_PER_MINUTE = 160


def log_tool_usage(tool_name: str, detail: str) -> None:
    print(f"[TOOL] {tool_name}: {detail}")


def load_urls(file_path: Path) -> List[str]:
    log_tool_usage("FileRead", f"Loading URLs from {file_path}")
    if not file_path.exists():
        raise FileNotFoundError(f"URL source file not found: {file_path}")

    urls = [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if not urls:
        raise ValueError(f"No URLs found in {file_path}")

    return urls


def fetch_html(url: str) -> str:
    log_tool_usage("requests.get", f"Fetching {url}")
    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/129.0.0.0 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    return response.text


def extract_article_text(html: str) -> str:
    log_tool_usage("BeautifulSoup", "Extracting article text")
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements including nav, ads, forms, footers, headers
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer",
                     "aside", "form", "button", "iframe", "svg", "meta"]):
        tag.decompose()

    # Remove elements with common navigation/marketing class names
    for tag in soup.find_all(class_=re.compile(
        r"(nav|menu|sidebar|footer|header|subscribe|newsletter|ad|advertisement|"
        r"cookie|social|share|comment|related|recommend)", re.I)):
        tag.decompose()

    # Remove LaTeX/MathML content
    for tag in soup.find_all(["math", "annotation", "semantics"]):
        tag.decompose()

    # Remove span elements with mathematical display classes
    for tag in soup.find_all("span", class_=re.compile(r"(math|latex|displaystyle|texhtml)", re.I)):
        tag.decompose()

    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(strip=True)
    ]

    return "\n".join(paragraphs)


def clean_text_for_tts(text: str) -> str:
    """Remove LaTeX, mathematical symbols, and problematic characters for TTS."""
    # Remove LaTeX expressions like {\displaystyle ...}, {\\mathcal{A}}, etc.
    text = re.sub(r'\{\\?[a-z]+style[^}]*\}', '', text, flags=re.I)
    text = re.sub(r'\{\\?[a-z]+\{[^}]*\}\}', '', text, flags=re.I)
    text = re.sub(r'\{[^}]{0,3}\}', '', text)  # Remove short brace content

    # Remove standalone mathematical symbols and Greek letters
    text = re.sub(r'[α-ωΑ-Ω]', '', text)  # Greek letters
    text = re.sub(r'[∈∑∏∫∂∆∇≤≥≠≈∞⊂⊃∪∩∧∨¬∀∃]', '', text)  # Math symbols
    text = re.sub(r'[×÷±≡⊕⊗]', '', text)  # Operators

    # Remove citation markers like [ 1 ], [ 71 ], etc.
    text = re.sub(r'\[\s*\d+\s*\]', '', text)

    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def iter_sentences(text: str) -> Iterable[str]:
    # Clean text first
    text = clean_text_for_tts(text)
    sentence_endings = re.compile(r"(?<=[.!?])\s+")
    for sentence in sentence_endings.split(text):
        cleaned = sentence.strip()
        if cleaned:
            yield cleaned


def summarize_text(text: str, max_sentences: int) -> str:
    log_tool_usage("Summarizer", f"Selecting top {max_sentences} sentences")
    sentences = list(iter_sentences(text))
    if not sentences:
        return "No readable content found."

    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    word_freq = {}
    for word in re.findall(r"\b\w+\b", text.lower()):
        if len(word) <= 3:
            continue
        word_freq[word] = word_freq.get(word, 0) + 1

    sentence_scores: List[Tuple[float, str]] = []
    for sentence in sentences:
        words = re.findall(r"\b\w+\b", sentence.lower())
        if not words:
            continue
        score = sum(word_freq.get(word, 0) for word in words) / len(words)
        sentence_scores.append((score, sentence))

    if not sentence_scores:
        return " ".join(sentences[:max_sentences])

    top_sentences = sorted(sentence_scores, key=lambda item: item[0], reverse=True)[
        :max_sentences
    ]
    selected = [sentence for _, sentence in sorted(top_sentences, key=lambda x: sentences.index(x[1]))]

    return " ".join(selected)


def save_summaries(entries: List[str], file_path: Path) -> None:
    log_tool_usage("FileWrite", f"Writing summaries to {file_path}")
    file_path.write_text("\n\n".join(entries), encoding="utf-8")


def estimate_audio_hours(word_count: int, wpm: int = WORDS_PER_MINUTE) -> float:
    if word_count == 0 or wpm <= 0:
        return 0.0
    minutes = word_count / wpm
    return minutes / 60


def run_web_fetch(
    urls_file: Optional[Path] = None, summary_file: Optional[Path] = None
) -> Tuple[int, float, Path]:
    source_file = urls_file or DEFAULT_URLS_FILE
    output_file = summary_file or DEFAULT_SUMMARY_FILE

    urls = load_urls(source_file)
    entries: List[str] = []
    total_estimated_hours = 0.0

    for url in urls:
        try:
            html = fetch_html(url)
            article_text = extract_article_text(html)
            # Clean the article text for TTS
            article_text = clean_text_for_tts(article_text)
            word_count = len(re.findall(r"\b\w+\b", article_text))
            summary = summarize_text(article_text, MAX_SENTENCES_PER_SUMMARY)
            estimated_hours = estimate_audio_hours(word_count)
            total_estimated_hours += estimated_hours

            entry = "\n".join(
                [
                    f"URL: {url}",
                    f"Word count: {word_count}",
                    f"Estimated audio hours (@{WORDS_PER_MINUTE} wpm): {estimated_hours:.2f}",
                    "Summary:",
                    summary,
                    "Full content:",
                    article_text if article_text else "(No article text extracted.)",
                ]
            )
            entries.append(entry)
        except Exception as exc:  # noqa: BLE001
            entries.append(f"URL: {url}\nError: {exc}")

    save_summaries(entries, output_file)
    if total_estimated_hours < 20:
        print(
            "Warning: total estimated hours are below 20. Add more URLs or richer sources "
            "to increase content volume."
        )

    return len(entries), total_estimated_hours, output_file


def main() -> None:
    topic = os.getenv("TOPIC")

    if topic:
        urls_file = topic_file(topic, "result_url")
        summaries_file = topic_file(topic, "summaries")
    else:
        urls_file = DEFAULT_URLS_FILE
        summaries_file = DEFAULT_SUMMARY_FILE

    count, hours, output_file = run_web_fetch(urls_file, summaries_file)
    print(
        f"Saved {count} entries to {output_file} "
        f"(estimated {hours:.2f} total audio hours)."
    )


if __name__ == "__main__":
    main()