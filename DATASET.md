# Dataset

## Source and link

- **Dataset:** Enron Email Dataset (with optional attachments)
- **Link:** https://www.kaggle.com/datasets/wcukierski/enron-email-dataset
- **Format:** The project uses a preprocessed CSV export (`data/emails.csv`) with columns `file` and `message`, where `message` is the raw email (RFC 822–style headers + body).

## How the slice was selected

1. **Source data:** Emails were loaded from `emails.csv` (Enron corpus export from Kaggle).
2. **Parsing:** Each raw `message` was parsed to extract `message_id`, `date`, `from`, `to`, `subject`, and plain-text `body` (split on double newline after headers; fallback to `X-FileName` boundary when present).
3. **Subject normalization:** Subject lines were normalized to a canonical form (`subject_clean`: strip Re:/Fwd:, lowercase, collapse whitespace) so that threads could be grouped by subject.
4. **Filtering:** Rows with empty or trivial `subject_clean` (e.g. "re", "test") were dropped.
5. **Date window:** A 3–6 month date range was applied to keep the slice coherent and of manageable size (exact window is configurable in the cleaning notebook).
6. **Thread selection:** Threads were grouped by `subject_clean`. We selected the top threads by message count until reaching roughly 100–300+ messages in total (or more, depending on run); each thread was assigned a stable `thread_id` (e.g. `T-001`, `T-002`, …).
7. **Attachments:** The current slice indexes **email bodies only**. Attachment extraction (PDF/DOC/TXT/HTML) and chunking with `page_no` can be added via the indexer (see README and `ingest.py`).

## Final counts and size

- **Threads:** 15 (or as produced by the last run of the dataset-cleaning notebook).
- **Messages:** ~25,000+ (exact count from `len(threaded_emails)` in the notebook / indexer output).
- **Attachments:** 0 in the current email-only slice (assignment target 20–50 attachments is optional; add attachment indexing to reach it).
- **Approximate indexed text size:** ~1.5–2 MB (sum of body lengths).

These numbers may vary slightly between runs; the authoritative counts are those printed when running `ingest.py` or the dataset-cleaning notebook.

## Preprocessing

- Header/body split for plain-text body extraction.
- Subject normalization for thread grouping.
- Date kept as parsed string for display and filtering.
- No OCR or attachment text extraction in the default pipeline (add in `ingest.py` if needed).

## License

The Enron corpus is widely used in research and is typically treated as **public domain** or **research-only**. The Kaggle dataset page and the original Enron corpus documentation should be consulted for the exact terms. This project does not claim ownership of the underlying data; use and redistribution should comply with Kaggle’s and the Enron corpus’s terms.
