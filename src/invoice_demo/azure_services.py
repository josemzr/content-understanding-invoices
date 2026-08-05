from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalysisInput
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.identity import DefaultAzureCredential

from invoice_demo.config import Settings
from invoice_demo.models import (
    AnalysisReport,
    ExtractedDocument,
    normalize_field,
)
from invoice_demo.templates import all_analyzers

DI_FIELD_ALIASES = {
    "VendorName": "SupplierName",
    "VendorTaxId": "SupplierTaxId",
    "InvoiceId": "InvoiceNumber",
    "CustomerName": "RecipientName",
    "CustomerAddress": "RecipientAddress",
    "PurchaseOrder": "PurchaseOrderNumber",
    "SubTotal": "Subtotal",
    "TotalTax": "TaxAmount",
    "InvoiceTotal": "TotalAmount",
    "DueDate": "PaymentDueDate",
    "Items": "LineItems",
}

DI_LINE_ITEM_ALIASES = {
    "ProductCode": "SupplierItemCode",
    "Unit": "UnitOfMeasure",
}


def _rename_keys(value: Any, aliases: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {aliases.get(key, key): _rename_keys(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [_rename_keys(item, aliases) for item in value]
    return value


class AzureDocumentServices:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._credential = DefaultAzureCredential()
        self._content_understanding: ContentUnderstandingClient | None = None
        self._document_intelligence: DocumentIntelligenceClient | None = None

    @property
    def content_understanding(self) -> ContentUnderstandingClient:
        if self._content_understanding is None:
            self._content_understanding = ContentUnderstandingClient(
                endpoint=self._settings.require_content_understanding_endpoint(),
                credential=self._credential,
            )
        return self._content_understanding

    @property
    def document_intelligence(self) -> DocumentIntelligenceClient:
        if self._document_intelligence is None:
            self._document_intelligence = DocumentIntelligenceClient(
                endpoint=self._settings.require_document_intelligence_endpoint(),
                credential=self._credential,
            )
        return self._document_intelligence

    def close(self) -> None:
        if self._content_understanding is not None:
            self._content_understanding.close()
        if self._document_intelligence is not None:
            self._document_intelligence.close()
        self._credential.close()

    def setup_analyzers(self, *, replace: bool = False) -> list[dict[str, Any]]:
        deployments = self._settings.model_deployments()
        if deployments:
            self.content_understanding.update_defaults(model_deployments=deployments)

        created: list[dict[str, Any]] = []
        for definition in all_analyzers(
            self._settings.completion_model,
            self._settings.embedding_model,
        ):
            analyzer_id = definition["analyzerId"]
            analyzer = self.content_understanding.begin_create_analyzer(
                analyzer_id,
                definition,
                allow_replace=replace,
            ).result()
            created.append(
                {
                    "analyzer_id": analyzer.analyzer_id,
                    "status": analyzer.status,
                    "models": dict(analyzer.models or {}),
                }
            )
        return created

    def inspect_analyzer(self, analyzer_id: str) -> dict[str, Any]:
        analyzer = self.content_understanding.get_analyzer(analyzer_id)
        supported = analyzer.supported_models
        return {
            "analyzer_id": analyzer.analyzer_id,
            "status": analyzer.status,
            "models": dict(analyzer.models or {}),
            "supported_models": {
                "completion": list(supported.completion or []) if supported else [],
                "embedding": list(supported.embedding or []) if supported else [],
            },
        }

    def analyze_content_understanding(
        self,
        document_path: Path,
        analyzer_id: str,
    ) -> AnalysisReport:
        document = document_path.read_bytes()
        mime_type = mimetypes.guess_type(document_path.name)[0] or "application/octet-stream"
        started = time.perf_counter()
        poller = self.content_understanding.begin_analyze(
            analyzer_id,
            inputs=[AnalysisInput(data=document, name=document_path.name, mime_type=mime_type)],
            model_deployments=self._settings.model_deployments(),
        )
        result = poller.result()
        duration_ms = (time.perf_counter() - started) * 1000

        documents: list[ExtractedDocument] = []
        for content in result.contents:
            if not content.fields:
                continue
            start_page = getattr(content, "start_page_number", None)
            end_page = getattr(content, "end_page_number", None)
            page_range = (
                f"{start_page}-{end_page}"
                if start_page is not None and end_page is not None
                else None
            )
            documents.append(
                ExtractedDocument(
                    document_type=content.category or content.analyzer_id or analyzer_id,
                    analyzer_id=content.analyzer_id or analyzer_id,
                    page_range=page_range,
                    fields={name: normalize_field(value) for name, value in content.fields.items()},
                )
            )

        usage = poller.usage
        usage_dict = usage.as_dict() if usage is not None else {}
        return AnalysisReport(
            provider="content_understanding",
            analyzer_id=analyzer_id,
            duration_ms=round(duration_ms, 2),
            documents=documents,
            usage=usage_dict,
        )

    def analyze_document_intelligence(
        self,
        document_path: Path,
        model_id: str = "prebuilt-invoice",
    ) -> AnalysisReport:
        started = time.perf_counter()
        poller = self.document_intelligence.begin_analyze_document(
            model_id,
            AnalyzeDocumentRequest(bytes_source=document_path.read_bytes()),
        )
        result = poller.result()
        duration_ms = (time.perf_counter() - started) * 1000

        documents: list[ExtractedDocument] = []
        for document in result.documents or []:
            fields = {}
            for name, value in (document.fields or {}).items():
                source = [region.as_dict() for region in value.bounding_regions or []]
                normalized = normalize_field(value, source=source or None)
                canonical_name = DI_FIELD_ALIASES.get(name, name)
                if canonical_name == "LineItems":
                    normalized.value = _rename_keys(normalized.value, DI_LINE_ITEM_ALIASES)
                fields[canonical_name] = normalized
            documents.append(
                ExtractedDocument(
                    document_type=document.doc_type,
                    analyzer_id=model_id,
                    confidence=document.confidence,
                    fields=fields,
                )
            )

        return AnalysisReport(
            provider="document_intelligence",
            analyzer_id=model_id,
            duration_ms=round(duration_ms, 2),
            documents=documents,
            usage={"document_pages": len(result.pages)},
        )
