#!/usr/bin/env python3
"""
Indexer script: build threaded_emails.json (and optional attachment chunks) from source data.
Run from project root: python ingest.py [--emails-csv path] [--output path]
If data/emails.csv is missing, use data/threaded_emails.json if present; otherwise exit with instructions.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("ingest.py requires pandas. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)


def parse_email(raw: str) -> dict:
    """Extract message_id, date, from, to, subject, body from raw email text."""
    if not isinstance(raw, str):
        return {}
    data = {}
    fields = [
        "Message-ID", "Date", "From", "To", "Cc", "Subject",
        "X-From", "X-To", "X-Folder",
    ]
    for field in fields:
        match = re.search(rf"{field}:\s*(.*)", raw, re.IGNORECASE)
        key = field.lower().replace("-", "_")  # Cc -> cc
        data[key] = (match.group(1).strip() if match else "").strip()
    parts = raw.split("\n\n", 1)
    data["body"] = (parts[1].strip() if len(parts) > 1 else "").strip()
    if "message-id" in data and data["message_id"]:
        data["message_id"] = data.pop("message_id", data.get("message_id", ""))
    else:
        data["message_id"] = data.get("message_id", "")
    return data


def normalize_subject(subject: str) -> str:
    if not isinstance(subject, str):
        return ""
    s = subject.lower().strip()
    s = re.sub(r"^(re|fw|fwd)\s*:\s*", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into chunks of ~chunk_size chars with overlap (for ~200-400 token chunks)."""
    if not text or chunk_size <= 0:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    """Return list of (1-based page number, text) for each page. Requires pymupdf."""
    try:
        import fitz  # pymupdf
    except ImportError:
        return []
    out = []
    try:
        doc = fitz.open(path)
        for i in range(len(doc)):
            page = doc[i]
            out.append((i + 1, (page.get_text() or "").strip()))
        doc.close()
    except Exception:
        pass
    return out


def extract_txt(path: Path) -> list[tuple[int, str]]:
    """Return [(1, full_text)] for a single-page text file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        return [(1, text)] if text else []
    except Exception:
        return []


def extract_html(path: Path) -> list[tuple[int, str]]:
    """Return [(1, text)] with tags stripped (simple regex)."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return [(1, text)] if text else []
    except Exception:
        return []


def run_attachment_ingest(attachments_dir: Path, output_path: Path, message_id_from_name: str = "") -> None:
    """Scan attachments_dir for PDF/TXT/HTML, extract text, chunk, write attachment_chunks.json."""
    if not attachments_dir.exists():
        return
    chunks_out = []
    doc_idx = [0]  # mutable for closure

    def add_chunks(message_id: str, page_no: int, text: str, thread_id: str = "") -> None:
        for block in chunk_text(text, chunk_size=800, overlap=100):
            chunks_out.append({
                "doc_id": f"att_{doc_idx[0]}",
                "message_id": message_id,
                "page_no": page_no,
                "text": block,
                "thread_id": thread_id,
            })
            doc_idx[0] += 1

    for f in attachments_dir.rglob("*.pdf"):
        for page_no, text in extract_pdf_pages(f):
            add_chunks(message_id_from_name or f"att_{f.stem}", page_no, text)
    for f in attachments_dir.rglob("*.txt"):
        for page_no, text in extract_txt(f):
            add_chunks(message_id_from_name or f"att_{f.stem}", page_no, text)
    for f in attachments_dir.rglob("*.html"):
        for page_no, text in extract_html(f):
            add_chunks(message_id_from_name or f"att_{f.stem}", page_no, text)

    if chunks_out:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(chunks_out, f, indent=2)
        print(f"Wrote {len(chunks_out)} attachment chunks to {output_path}.")


def run_ingest(
    emails_csv: Path,
    output_path: Path,
    max_messages: int = 50000,
    max_threads: int | None = None,
) -> None:
    """Load emails from CSV, parse, thread, and write threaded_emails.json."""
    if not emails_csv.exists():
        raise FileNotFoundError(
            f"Emails CSV not found: {emails_csv}. "
            "Download the Enron dataset (e.g. from Kaggle) and place emails.csv in data/, or run the dataset_cleaning notebook first."
        )
    df = pd.read_csv(emails_csv)
    if "message" not in df.columns:
        raise ValueError("CSV must have a 'message' column with raw email content.")
    parsed = df["message"].apply(parse_email)
    email_df = pd.json_normalize(parsed)
    df_clean = pd.concat([df[["file", "message"]], email_df], axis=1)
    df_clean["subject_clean"] = df_clean["subject"].fillna("").apply(normalize_subject)
    df_clean = df_clean[df_clean["subject_clean"] != ""]
    df_clean = df_clean[~df_clean["subject_clean"].isin(["re", "test"])]
    thread_sizes = df_clean.groupby("subject_clean").size().sort_values(ascending=False)
    selected = []
    count = 0
    for subj, size in thread_sizes.items():
        selected.append(subj)
        count += size
        if count >= max_messages:
            break
        if max_threads is not None and len(selected) >= max_threads:
            break
    dataset = df_clean[df_clean["subject_clean"].isin(selected)].copy()
    thread_map = {s: f"T-{i:03d}" for i, s in enumerate(selected, start=1)}
    dataset["thread_id"] = dataset["subject_clean"].map(thread_map)
    out_cols = [
        "message_id", "date", "from", "to", "cc", "subject", "body",
        "subject_clean", "thread_id", "x_from", "x_to", "x_folder", "file",
    ]
    out_cols = [c for c in out_cols if c in dataset.columns]
    records = dataset[out_cols].to_dict(orient="records")
    for i, r in enumerate(records):
        r["doc_id"] = f"em_{i}"
        for k, v in list(r.items()):
            if pd.isna(v):
                r[k] = None
            elif hasattr(v, "item"):
                try:
                    r[k] = v.item()
                except (ValueError, AttributeError):
                    r[k] = str(v)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)
    n_threads = dataset["thread_id"].nunique()
    n_msgs = len(dataset)
    size_mb = dataset["body"].str.len().sum() / (1024 * 1024)
    print(f"Wrote {output_path}: {n_threads} threads, {n_msgs} messages, ~{size_mb:.2f} MB text.")


def main():
    parser = argparse.ArgumentParser(description="Build threaded_emails.json and optional attachment_chunks.json")
    parser.add_argument(
        "--emails-csv",
        type=Path,
        default=Path("data/emails.csv"),
        help="Path to emails CSV (default: data/emails.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/threaded_emails.json"),
        help="Output path for threaded emails JSON (default: data/threaded_emails.json)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=50000,
        help="Max messages to include (by adding threads in size order). Use 300 for assignment-style slice.",
    )
    parser.add_argument(
        "--max-threads",
        type=int,
        default=None,
        help="Max threads to include (e.g. 20 for 10–20 thread slice). Optional.",
    )
    parser.add_argument(
        "--attachments-dir",
        type=Path,
        default=None,
        help="Optional: directory of PDF/TXT/HTML attachments to index (writes data/attachment_chunks.json)",
    )
    args = parser.parse_args()
    try:
        run_ingest(args.emails_csv, args.output, args.max_messages, args.max_threads)
    except FileNotFoundError as e:
        if args.output.exists():
            print(f"Note: {args.emails_csv} not found; using existing {args.output}.", file=sys.stderr)
        else:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if args.attachments_dir is not None:
        run_attachment_ingest(
            args.attachments_dir,
            Path("data/attachment_chunks.json"),
        )


if __name__ == "__main__":
    main()
