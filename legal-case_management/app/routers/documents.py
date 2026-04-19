"""Documents router — endpoints for processing case documents."""

import logging
from fastapi import APIRouter, HTTPException

from app.models import ProcessRequest, CaseData
from app.processing.document_processor import process_all_documents
from app.retrieval.indexer import index_case_documents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

#in-memory store for processed case data .
_case_store: dict[str, CaseData] = {}


def get_case_data(case_number: str) -> CaseData | None:
    return _case_store.get(case_number)


@router.post("/process", response_model=dict)
async def process_documents(request: ProcessRequest):
    """Process all documents for a case: load → clean OCR → extract → index.

    This is the main entry point. It runs the full pipeline:
    1. Load raw documents from disk
    2. Classify each document by type
    3. Clean OCR noise (title search pages)
    4. Extract structured data via LLM (liens, deadlines, action items, etc.)
    5. Chunk and index in ChromaDB for retrieval

    Returns processing stats and a summary of what was extracted.
    """
    try:
        case_data = process_all_documents(request.data_dir)
        _case_store[case_data.case_number] = case_data

        index_stats = index_case_documents(case_data)

        doc_summaries = []
        for doc, ext in zip(case_data.documents, case_data.extractions):
            doc_summaries.append({
                "filename": doc.filename,
                "doc_type": doc.doc_type.value,
                "ocr_corrections": len(doc.ocr_corrections),
                "ocr_correction_details": doc.ocr_corrections[:10],
                "liens_extracted": len(ext.liens),
                "deadlines_extracted": len(ext.deadlines),
                "action_items_extracted": len(ext.action_items),
                "tax_records": len(ext.tax_info),
                "has_ownership_info": ext.ownership is not None,
                "other_facts": len(ext.other_facts),
            })

        return {
            "status": "success",
            "case_number": case_data.case_number,
            "borrower": case_data.borrower,
            "property": case_data.property_address,
            "documents_processed": len(case_data.documents),
            "indexing": index_stats,
            "document_details": doc_summaries,
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Document processing failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/case/{case_number}", response_model=dict)
async def get_case(case_number: str):
    """Get processed case data including all extractions."""
    case_data = _case_store.get(case_number)
    if not case_data:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_number} not found. Run /documents/process first.",
        )

    return {
        "case_number": case_data.case_number,
        "borrower": case_data.borrower,
        "property": case_data.property_address,
        "county": case_data.county,
        "state": case_data.state,
        "documents": [
            {
                "filename": d.filename,
                "doc_type": d.doc_type.value,
                "ocr_corrections": d.ocr_corrections,
            }
            for d in case_data.documents
        ],
        "extractions": [ext.model_dump() for ext in case_data.extractions],
    }


@router.get("/case/{case_number}/extractions", response_model=dict)
async def get_extractions(case_number: str):
    """Get just the structured extractions for a case."""
    case_data = _case_store.get(case_number)
    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case {case_number} not found.")

    all_liens = []
    all_deadlines = []
    all_action_items = []
    all_tax = []
    ownership = None

    for ext in case_data.extractions:
        all_liens.extend([l.model_dump() for l in ext.liens])
        all_deadlines.extend([d.model_dump() for d in ext.deadlines])
        all_action_items.extend([a.model_dump() for a in ext.action_items])
        all_tax.extend([t.model_dump() for t in ext.tax_info])
        if ext.ownership and not ownership:
            ownership = ext.ownership.model_dump()

    return {
        "case_number": case_number,
        "liens": all_liens,
        "deadlines": all_deadlines,
        "action_items": all_action_items,
        "tax_info": all_tax,
        "ownership": ownership,
    }
