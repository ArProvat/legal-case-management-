"""Pydantic models for documents, extractions"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Document types ──────────────────────────────────────────────

class DocumentType(str, Enum):
    TITLE_SEARCH = "title_search"
    COURT_ORDER = "court_order"
    SERVICER_EMAIL = "servicer_email"
    CASE_CONTEXT = "case_context"
    UNKNOWN = "unknown"


class RawDocument(BaseModel):
    """A document as-uploaded, before processing."""
    filename: str
    content: str
    doc_type: DocumentType = DocumentType.UNKNOWN


class ProcessedDocument(BaseModel):
    """A document after OCR cleaning and structuring."""
    filename: str
    doc_type: DocumentType
    original_content: str
    cleaned_content: str
    ocr_corrections: list[str] = Field(default_factory=list)


# ── Extracted structured data ───────────────────────────────────

class Lien(BaseModel):
    position: int
    description: str
    holder: str
    amount: Optional[float] = None
    date_recorded: Optional[str] = None
    instrument_number: Optional[str] = None
    status: Optional[str] = None
    source_file: str = ""


class Deadline(BaseModel):
    date: str
    description: str
    requirements: Optional[str] = None
    source_file: str = ""


class ActionItem(BaseModel):
    priority: str = "NORMAL"
    description: str
    source_file: str = ""
    due_date: Optional[str] = None


class TaxInfo(BaseModel):
    year: int
    status: str
    amount: float
    parcel_number: Optional[str] = None
    source_file: str = ""


class OwnershipRecord(BaseModel):
    current_owner: str
    vesting: Optional[str] = None
    prior_owners: list[str] = Field(default_factory=list)
    source_file: str = ""


class StructuredExtraction(BaseModel):
    """All structured data extracted from a single document."""
    doc_type: DocumentType
    filename: str
    liens: list[Lien] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    tax_info: list[TaxInfo] = Field(default_factory=list)
    ownership: Optional[OwnershipRecord] = None
    other_facts: list[str] = Field(default_factory=list)

class ProcessRequest(BaseModel):
    case_number: str = "2025-FC-08891"
    data_dir: Optional[str] = None

class CaseData(BaseModel):
    case_number: str
    borrower: str
    property_address: str
    county: str
    state: str
    documents: list[ProcessedDocument] = Field(default_factory=list)
    extractions: list[StructuredExtraction] = Field(default_factory=list)