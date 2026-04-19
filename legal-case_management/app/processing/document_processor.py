# Orchestrator

import json
import logging
from pathlib import Path
from openai import OpenAI

from app.config import settings
from app.models import (
    RawDocument,
    ProcessedDocument,
    DocumentType,
    CaseData,
)
from app.processing.ocr_cleaner import clean_ocr_text
from app.processing.extractors import extract_structured_data

logger = logging.getLogger(__name__)


def classify_document(filename: str, content: str) -> DocumentType:
    """Classify a document based on filename and content heuristics."""
    fname = filename.lower()
    if "title_search" in fname or "schedule_b" in fname:
        return DocumentType.TITLE_SEARCH
    if "court_order" in fname or "order" in fname:
        return DocumentType.COURT_ORDER
    if "servicer" in fname or "email" in fname:
        return DocumentType.SERVICER_EMAIL
    if "case_context" in fname or fname.endswith(".json"):
        return DocumentType.CASE_CONTEXT

    content_lower = content[:500].lower()
    if "schedule b" in content_lower or "title insurance" in content_lower:
        return DocumentType.TITLE_SEARCH
    if "ordered and adjudged" in content_lower or "circuit court" in content_lower:
        return DocumentType.COURT_ORDER
    if "servicing transfer" in content_lower or "dear counsel" in content_lower:
        return DocumentType.SERVICER_EMAIL

    return DocumentType.UNKNOWN


def load_raw_documents(data_dir: str) -> list[RawDocument]:
    """Load all documents from a directory."""
    docs = []
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    for filepath in sorted(data_path.iterdir()):
        if filepath.is_file():
            content = filepath.read_text(encoding="utf-8", errors="replace")
            doc_type = classify_document(filepath.name, content)
            docs.append(
                RawDocument(filename=filepath.name, content=content, doc_type=doc_type)
            )
            logger.info(f"Loaded {filepath.name} as {doc_type.value}")

    return docs


def process_document(raw: RawDocument) -> ProcessedDocument:
    """Clean a single document: apply OCR correction if needed."""
    if raw.doc_type == DocumentType.TITLE_SEARCH:
        cleaned, corrections = clean_ocr_text(raw.content)
        logger.info(f"OCR cleaning for {raw.filename}: {len(corrections)} corrections")
    else:
        cleaned = raw.content
        corrections = []

    return ProcessedDocument(
        filename=raw.filename,
        doc_type=raw.doc_type,
        original_content=raw.content,
        cleaned_content=cleaned,
        ocr_corrections=corrections,
    )


def process_all_documents(data_dir: str | None = None) -> CaseData:
    """Full pipeline: load → classify → clean → extract → aggregate.

    Returns a CaseData object with all processed docs and extractions.
    """
    data_dir = data_dir or settings.data_dir
    client = OpenAI(api_key=settings.openai_api_key)
    raw_docs = load_raw_documents(data_dir)

    case_number = "UNKNOWN"
    borrower = "UNKNOWN"
    property_address = "UNKNOWN"
    county = "UNKNOWN"
    state = "UNKNOWN"

    for raw in raw_docs:
        if raw.doc_type == DocumentType.CASE_CONTEXT:
            try:
                ctx = json.loads(raw.content)
                case_number = ctx.get("case_number", case_number)
                borrower = ctx.get("borrower", borrower)
                property_address = ctx.get("property_address", property_address)
                county = ctx.get("county", county)
                state = ctx.get("state", state)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse case context: {raw.filename}")

    processed_docs = []
    extractions = []

    for raw in raw_docs:
        # Step 1: OCR clean
        proc = process_document(raw)
        processed_docs.append(proc)

        # Step 2: LLM extraction
        extraction = extract_structured_data(
            cleaned_text=proc.cleaned_content,
            doc_type=proc.doc_type,
            filename=proc.filename,
            client=client,
        )
        extractions.append(extraction)
        logger.info(
            f"Extracted from {proc.filename}: "
            f"{len(extraction.liens)} liens, "
            f"{len(extraction.deadlines)} deadlines, "
            f"{len(extraction.action_items)} action items"
        )

    return CaseData(
        case_number=case_number,
        borrower=borrower,
        property_address=property_address,
        county=county,
        state=state,
        documents=processed_docs,
        extractions=extractions,
    )
