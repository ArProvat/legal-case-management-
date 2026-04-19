# LLM structured extraction
import json
import logging
from openai import OpenAI

from app.config import settings
from app.models import (
    DocumentType,
    StructuredExtraction,
    Lien,
    Deadline,
    ActionItem,
    TaxInfo,
    OwnershipRecord,
)

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "liens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "position": {"type": "integer"},
                    "description": {"type": "string"},
                    "holder": {"type": "string"},
                    "amount": {"type": ["number", "null"]},
                    "date_recorded": {"type": ["string", "null"]},
                    "instrument_number": {"type": ["string", "null"]},
                    "status": {"type": ["string", "null"]},
                },
                "required": ["position", "description", "holder"],
            },
        },
        "deadlines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                    "requirements": {"type": ["string", "null"]},
                },
                "required": ["date", "description"],
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string", "enum": ["URGENT", "HIGH", "NORMAL", "LOW"]},
                    "description": {"type": "string"},
                    "due_date": {"type": ["string", "null"]},
                },
                "required": ["priority", "description"],
            },
        },
        "tax_info": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "status": {"type": "string"},
                    "amount": {"type": "number"},
                    "parcel_number": {"type": ["string", "null"]},
                },
                "required": ["year", "status", "amount"],
            },
        },
        "ownership": {
            "type": ["object", "null"],
            "properties": {
                "current_owner": {"type": "string"},
                "vesting": {"type": ["string", "null"]},
                "prior_owners": {"type": "array", "items": {"type": "string"}},
            },
        },
        "other_facts": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["liens", "deadlines", "action_items", "tax_info", "other_facts"],
}

SYSTEM_PROMPT = """You are a legal document extraction engine. Given a cleaned document,
extract ALL structured data into the specified JSON schema. Be precise:
- For liens: include every lien/mortgage/assignment/lis pendens. Include amounts,
  dates, and instrument numbers exactly as they appear.
- For deadlines: include every date that requires action, with what must happen.
- For action items: extract every task, instruction, or requirement. Assign
  priority (URGENT for court deadlines/rejections, HIGH for time-sensitive,
  NORMAL for standard tasks, LOW for informational).
- For tax info: year, paid/unpaid status, and amounts.
- For ownership: current owner, vesting type, chain of title.
- For other_facts: anything important not captured above (easements, covenants,
  counsel info, contact details, servicer addresses).

IMPORTANT: Extract ONLY what is explicitly stated in the document. Never infer
or fabricate data. If a field is not present, use null."""


def extract_structured_data(
    cleaned_text: str,
    doc_type: DocumentType,
    filename: str,
    client: OpenAI | None = None,
) -> StructuredExtraction:
    """Use OpenAI to extract structured data from cleaned document text."""
    if client is None:
        client = OpenAI(api_key=settings.openai_api_key)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Document type: {doc_type.value}\n"
                        f"Filename: {filename}\n\n"
                        f"--- DOCUMENT CONTENT ---\n{cleaned_text}\n--- END ---\n\n"
                        "Extract all structured data into the JSON schema."
                    ),
                },
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "store_extraction",
                        "description": "Store the extracted structured data",
                        "parameters": EXTRACTION_SCHEMA,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "store_extraction"}},
            temperature=0.0,
        )

        tool_call = response.choices[0].message.tool_calls[0]
        data = json.loads(tool_call.function.arguments)

        liens = [Lien(source_file=filename, **l) for l in data.get("liens", [])]
        deadlines = [Deadline(source_file=filename, **d) for d in data.get("deadlines", [])]
        action_items = [ActionItem(source_file=filename, **a) for a in data.get("action_items", [])]
        tax_info = [TaxInfo(source_file=filename, **t) for t in data.get("tax_info", [])]

        ownership = None
        if data.get("ownership"):
            ownership = OwnershipRecord(source_file=filename, **data["ownership"])

        return StructuredExtraction(
            doc_type=doc_type,
            filename=filename,
            liens=liens,
            deadlines=deadlines,
            action_items=action_items,
            tax_info=tax_info,
            ownership=ownership,
            other_facts=data.get("other_facts", []),
        )

    except Exception as e:
        logger.error(f"Extraction failed for {filename}: {e}")
        return StructuredExtraction(
            doc_type=doc_type,
            filename=filename,
            other_facts=[f"Extraction error: {str(e)}"],
        )
