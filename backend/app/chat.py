"""AI Chat Assistant — answers free-form pupil questions using RAG.

The LLM is grounded entirely in retrieved textbook chunks, the same KB
used by the assessor.  We limit output to 300 tokens and apply light
repetition penalties to stop the 1B model from looping.

Rate limit: MAX_TURNS per session, tracked in-process (resets on restart).
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

from .kb.retriever import search_notes, dense_search
from .llm import generate_text
from .remote_llm import RemoteUnavailable
from . import prompts

MAX_TURNS = 10          # messages per session (reset on restart or re-login)
MAX_Q_LEN = 500         # characters; trim silently
MAX_HISTORY = 3         # assistant turns kept in the prompt
MAX_NEW_TOKENS = 150
REPETITION_PENALTY = 1.0   # Set to 1.0: HF repetition_penalty penalises prompt words and forces gibberish rhyming loops
NO_REPEAT_NGRAM = 0        # Set to 0: prevents forced alphabet rhyming on 1B model
CHUNK_SEP = "\n---\n"
# Gates on the question's best bge-m3 match in the notes (RAG settings study, eval/results/rag_settings_detail.md):
# 0.35 loses no answerable question; off-syllabus questions above it are declined by the answer model, which gets
# the study's decline rule. The textbook-only fallback (no model reachable) cannot decline, so it keeps 0.55.
GATE = 0.35
GATE_TEXTBOOK_ONLY = 0.55

_counters: dict[int, int] = {}   # student_id -> turn count
_lock = threading.Lock()


@dataclass
class ChatSource:
    topic_rumi: str
    topic_jawi: str
    pages: list[int]


@dataclass
class ChatReply:
    reply: str
    sources: list[ChatSource]
    turns_left: int


class ChatLimitError(Exception):
    """Raised when the student has used all allowed chat turns."""


def reset_turns(student_id: int) -> None:
    """Reset the turn counter — call after login."""
    with _lock:
        _counters[student_id] = 0


def _increment(student_id: int) -> int:
    """Increment and return the NEW count.  Raises ChatLimitError if over limit."""
    with _lock:
        n = _counters.get(student_id, 0) + 1
        if n > MAX_TURNS:
            raise ChatLimitError(f"Had {MAX_TURNS} turns for this session.")
        _counters[student_id] = n
        return n


def _build_context(hits) -> str:
    """Format retrieved chunks into a readable block for the prompt."""
    parts = []
    for h in hits:
        meta = h.metadata
        pages = meta.get("book_pages") or []
        page_str = f" (ms. {', '.join(str(p) for p in pages)})" if pages else ""
        title = meta.get("section_rumi") or meta.get("topic_rumi") or ""
        parts.append(f"[{title}{page_str}]\n{h.text.strip()}")
    return CHUNK_SEP.join(parts) if parts else "(tiada petikan berkaitan ditemui)"


def _build_history(history: list) -> str:
    """Format recent turns into a readable block."""
    if not history:
        return "(tiada)"
    lines = []
    for turn in history[-MAX_HISTORY:]:
        if isinstance(turn, dict):
            role_val = turn.get("role", "")
            content_val = turn.get("content", "")
        else:
            role_val = getattr(turn, "role", "")
            content_val = getattr(turn, "content", "")
        role = "Murid" if role_val == "user" else "Bulan"
        lines.append(f"{role}: {str(content_val).strip()}")
    return "\n".join(lines)


def _clean(text: str) -> str:
    """Strip prompt echo and common artefacts from the LLM output."""
    text = re.sub(r"^[Jj]awapan\s+[Bb]ulan\s*:?\s*", "", text).strip()
    text = re.sub(r"^[Bb]ulan\s*:?\s*", "", text).strip()
    
    # Trim repetitive word loops if any
    words = text.split()
    seen: set[tuple] = set()
    for i in range(len(words) - 3):
        span = tuple(words[i : i + 4])
        if span in seen:
            text = " ".join(words[:i]).strip()
            break
        seen.add(span)
        
    # Cut cleanly at the last complete sentence if reasonably long
    last_punct = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    if last_punct > 50:
        text = text[: last_punct + 1].strip()

    return text.strip()


# Query intent detection mapping for KAFA UPKK topics
INTENT_SPECS = [
    {
        "intent": "fadhilat",
        "triggers": ["fadhilat", "kelebihan", "faedah", "hikmah", "ganjaran", "kebaikan"],
        "section_keywords": ["fadhilat", "kelebihan", "hikmah", "faedah"],
    },
    {
        "intent": "niat",
        "triggers": ["niat", "lafaz niat", "bacaan niat"],
        "section_keywords": ["lafaz niat", "niat"],
    },
    {
        "intent": "waktu",
        "triggers": ["bila waktu", "waktu", "masa", "bila boleh", "bila dilakukan"],
        "section_keywords": ["waktu", "pengertian"],
    },
    {
        "intent": "rakaat",
        "triggers": ["berapa rakaat", "bilangan rakaat", "jumlah rakaat", "rakaat"],
        "section_keywords": ["kaifiat", "pelaksanaan", "pengertian", "bilangan"],
    },
    {
        "intent": "hukum",
        "triggers": ["hukum"],
        "section_keywords": ["hukum", "pengertian"],
    },
    {
        "intent": "syarat",
        "triggers": ["syarat sah", "syarat wajib", "syarat"],
        "section_keywords": ["syarat"],
    },
    {
        "intent": "rukun",
        "triggers": ["rukun"],
        "section_keywords": ["rukun"],
    },
    {
        "intent": "kaifiat",
        "triggers": ["cara", "kaifiat", "langkah", "bagaimana nak", "bagaimana solat", "pelaksanaan"],
        "section_keywords": ["cara pelaksanaan", "kaifiat", "cara"],
    },
    {
        "intent": "bahagian",
        "triggers": ["bahagian", "jenis", "terbahagi", "kategori", "pembahagian"],
        "section_keywords": ["bahagian", "jenis"],
    },
    {
        "intent": "kadar",
        "triggers": ["kadar", "harakat", "panjang bacaan"],
        "section_keywords": ["kadar", "cara bacaan", "martabat"],
    },
    {
        "intent": "contoh",
        "triggers": ["contoh", "kalimah"],
        "section_keywords": ["contoh"],
    },
    {
        "intent": "pengertian",
        "triggers": ["pengertian", "maksud", "erti", "takrif", "apa itu", "apakah yang dimaksudkan", "definisi", "apakah"],
        "section_keywords": ["pengertian", "definisi", "ringkasan"],
    },
]


def _detect_intent(query: str) -> dict | None:
    """Detect the pedagogical intent of a pupil's question."""
    q_low = query.lower()
    for spec in INTENT_SPECS:
        for trig in spec["triggers"]:
            if trig in q_low:
                return spec
    return None


def _rerank_hits_by_intent(hits: list, intent_spec: dict | None) -> list:
    """Promote chunks whose section name matches the detected intent."""
    if not hits or not intent_spec:
        return hits
    target_kws = intent_spec["section_keywords"]
    matched = []
    others = []
    for h in hits:
        sec = (h.metadata.get("section") or "").lower()
        if any(kw in sec for kw in target_kws):
            matched.append(h)
        else:
            others.append(h)
    return matched + others


def _extract_anchor_fact(message: str, hits: list, intent_spec: dict | None = None) -> str:
    """Extract the most relevant concise factual sentence from the top retrieved chunks."""
    if not hits:
        return ""
    q_lower = message.lower()
    intent = intent_spec["intent"] if intent_spec else ""
    top_text = hits[0].text
    lines = [line.strip() for line in top_text.splitlines() if line.strip()]

    # Intent 1: Fadhilat / Kelebihan
    if intent == "fadhilat":
        fadhilat_items = []
        for line in lines:
            line_clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
            line_clean = re.sub(r"^\*\*Rumi:\*\*\s*", "", line_clean).strip()
            if "|" in line_clean:
                line_clean = line_clean.split("|")[0].strip()
            if len(line_clean) > 15 and not line_clean.lower().startswith("fadhilat"):
                fadhilat_items.append(line_clean)
        if fadhilat_items:
            return "Antara fadhilatnya ialah: " + "; ".join(fadhilat_items[:3]) + "."

    # Intent 2: Lafaz Niat
    if intent == "niat":
        for line in lines:
            if "Sahaja aku" in line or "sahaja aku" in line:
                clean = re.sub(r"^.*?Sahaja aku", "Sahaja aku", line).strip()
                if "|" in clean:
                    clean = clean.split("|")[0].strip()
                return f"Niatnya ialah: \"{clean}\""
        for line in lines:
            if any(term in line.lower() for term in ("niat", "lafaz")):
                clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
                if "|" in clean:
                    clean = clean.split("|")[0].strip()
                if len(clean) > 15:
                    return clean

    # Intent 3: Waktu
    if intent == "waktu":
        for line in lines:
            clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
            clean = re.sub(r"^\*\*Rumi:\*\*\s*", "", clean).strip()
            if any(w in clean.lower() for w in ("malam", "sebelum", "selepas", "waktu", "ketika")):
                if "|" in clean:
                    clean = clean.split("|")[0].strip()
                if len(clean) > 20:
                    return clean

    # Intent 4: Bilangan Rakaat
    if intent == "rakaat":
        for line in lines:
            clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
            clean = re.sub(r"^\*\*Rumi:\*\*\s*", "", clean).strip()
            if "rakaat" in clean.lower():
                if "|" in clean:
                    clean = clean.split("|")[0].strip()
                if len(clean) > 15:
                    return clean

    # Intent 5: Hukum
    if intent == "hukum":
        for line in lines:
            clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
            clean = re.sub(r"^\*\*Rumi:\*\*\s*", "", clean).strip()
            if any(w in clean.lower() for w in ("sunat", "wajib", "harus", "hukum")):
                if "|" in clean:
                    clean = clean.split("|")[0].strip()
                if len(clean) > 15:
                    return clean

    # Intent 6: Bahagian / Jenis
    if intent == "bahagian":
        for line in lines:
            clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
            clean = re.sub(r"^\*\*Rumi:\*\*\s*", "", clean).strip()
            if any(w in clean.lower() for w in ("terbahagi", "bahagian", "iaitu")):
                if "|" in clean:
                    clean = clean.split("|")[0].strip()
                if len(clean) > 15:
                    return clean

    # Fallback to definition (Pengertian / ialah / bermaksud)
    for line in lines:
        line_clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
        line_clean = re.sub(r"^\*\*Rumi:\*\*\s*", "", line_clean).strip()
        if any(term in line_clean.lower() for term in ("ialah", "bermaksud", "erti", "adalah")):
            if "|" in line_clean:
                line_clean = line_clean.split("|")[0].strip()
            if len(line_clean) > 20:
                return line_clean

    # Fallback to the first informative sentence in top hit
    for line in lines:
        if line.startswith("#") or line.startswith("Topik:") or line.startswith("Bahagian:"):
            continue
        line_clean = re.sub(r"^[-*#\d\.]+\s*", "", line).strip()
        line_clean = re.sub(r"^\*\*Rumi:\*\*\s*", "", line_clean).strip()
        if "|" in line_clean:
            line_clean = line_clean.split("|")[0].strip()
        if len(line_clean) > 25:
            return line_clean

    return ""


def ask(
    *,
    student_id: int,
    message: str,
    subject: str | None = None,
    history: list[dict] | None = None,
) -> ChatReply:
    """Answer a pupil's question using RAG + intent-aware extractive anchoring + local LLM.

    Parameters
    ----------
    student_id : int   — used for rate limiting only (no DB lookup)
    message    : str   — the pupil's question (Rumi or Jawi)
    subject    : str | None — hint to narrow the KB search
    history    : list[{role, content}] — recent conversation turns
    """
    count = _increment(student_id)
    message = message.strip()[:MAX_Q_LEN]
    history = history or []
    if subject and subject.lower() in ("ibadah", "fiqah"):
        subject = "fiqh"

    # 1. Detect query intent
    intent_spec = _detect_intent(message)

    # 2. Check vector database similarity score (ChromaDB dense embedding)
    top_dense = dense_search(message, k=1, subject=subject)
    top_dense_score = top_dense[0].score if top_dense else 0.0

    # 3. Retrieve relevant note chunks
    hits = search_notes(message, subject=subject, k=4)

    # 4. Rerank hits by intent to promote the exact matching section
    hits = _rerank_hits_by_intent(hits, intent_spec)

    has_syllabus_match = bool(hits and top_dense_score >= GATE)
    strong_match = bool(hits and top_dense_score >= GATE_TEXTBOOK_ONLY)

    hist_text = _build_history(history)
    sources: list[ChatSource] = []

    # Detect language for courteous notification
    en_indicators = {"what", "who", "where", "how", "why", "when", "is", "are", "can", "tell", "explain"}
    q_words_set = set(re.findall(r"\w+", message.lower()))
    is_en = len(q_words_set & en_indicators) >= 2 or ("the" in q_words_set and len(q_words_set & en_indicators) >= 1)
    db_missing_prefix = "This data is not in my database." if is_en else "Data ini tiada dalam pangkalan data saya."

    if has_syllabus_match and hits:
        # Prune context to the most focused chunks (top 2) so 3B model is laser focused
        context = _build_context(hits[:2])
        # a weak match may be off-syllabus: no "key fact" pushing an answer, the model decides from the passages
        anchor = _extract_anchor_fact(message, hits, intent_spec) if strong_match else ""
        anchor_prompt = f"\nFakta utama buku teks: {anchor}" if anchor else ""
        focus_prompt = f" Soalan ini bertanyakan tentang {intent_spec['intent']}. Jawab secara terus berfokuskan {intent_spec['intent']} sahaja." if intent_spec else ""
        system_instruction = prompts.render_paragraph("chat", focus=focus_prompt, anchor=anchor_prompt, decline=db_missing_prefix)
        user_content = f"Petikan rujukan buku teks:\n{context}\n\nPerbualan sebelum ini:\n{hist_text}\n\nSoalan murid: {message}"

        # Deduplicate sources by topic only when syllabus matches
        seen_topics: set[str] = set()
        for h in hits:
            tid = h.metadata.get("topic_id", "")
            if tid and tid not in seen_topics:
                seen_topics.add(tid)
                pages = h.metadata.get("book_pages") or []
                sources.append(ChatSource(
                    topic_rumi=h.metadata.get("topic_rumi", tid),
                    topic_jawi=h.metadata.get("topic_jawi", ""),
                    pages=pages,
                ))
    else:
        # Out-of-syllabus / missing in vector database
        anchor = ""
        system_instruction = prompts.render_paragraph("chat_outside", notice=db_missing_prefix)
        user_content = f"Perbualan sebelum ini:\n{hist_text}\n\nSoalan murid: {message}"

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_content},
    ]

    try:
        gen = generate_text(           # local Qwen, or the Qwen server on Google Colab if its link is saved
            messages,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.1,          # low temperature for stable, factual output
            repetition_penalty=REPETITION_PENALTY,
            no_repeat_ngram_size=NO_REPEAT_NGRAM,
        )
        reply = _clean(gen.text)
    except RemoteUnavailable:
        reply = ""                    # no model reachable: the textbook anchor below is used instead

    declined = "tiada dalam pangkalan data" in reply.lower() or "not in my database" in reply.lower()
    if has_syllabus_match and (declined or not (reply or anchor)):
        # the model found no answer in the passages, or there is nothing to show (no reply and no textbook
        # key fact, e.g. no model for a weak match): outside the notes
        has_syllabus_match, sources = False, []

    # Ensure out-of-database answers explicitly contain the requested notice
    if not has_syllabus_match:
        if not (reply.startswith(db_missing_prefix) or db_missing_prefix.lower() in reply.lower() or "tiada dalam pangkalan data" in reply.lower() or "not in my database" in reply.lower()):
            reply = f"{db_missing_prefix} {reply}".strip()

    # Bulletproof fallback: If generation is degenerate, too short, or missed the specialized intent
    use_anchor_fallback = False
    if anchor and has_syllabus_match and hits:
        if len(reply) < 15 or len(reply.split()) < 4:
            use_anchor_fallback = True
        elif intent_spec and intent_spec["intent"] in ("fadhilat", "niat", "hukum", "waktu", "rakaat", "kadar"):
            # Check if LLM drifted into generic definition rather than answering the intent
            if intent_spec["intent"] == "fadhilat" and ("fadhilat" not in reply.lower() or "ialah solat sunat" in reply.lower()):
                use_anchor_fallback = True
            elif intent_spec["intent"] == "rakaat" and "rakaat" not in reply.lower():
                use_anchor_fallback = True
            elif intent_spec["intent"] == "niat" and "sahaja aku" not in reply.lower():
                use_anchor_fallback = True

    if use_anchor_fallback:
        top_meta = hits[0].metadata
        topic_name = top_meta.get("topic_rumi") or "buku teks"
        pages = top_meta.get("book_pages") or []
        page_txt = f" (ms. {', '.join(str(p) for p in pages)})" if pages else ""
        reply = f"Berdasarkan buku teks {topic_name}{page_txt}, {anchor}"

    return ChatReply(
        reply=reply,
        sources=sources,
        turns_left=MAX_TURNS - count,
    )
