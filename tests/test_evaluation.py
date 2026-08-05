from invoice_demo.evaluation import evaluate_report, values_match
from invoice_demo.models import AnalysisReport, ExtractedDocument, ExtractedField


def test_values_match_normalizes_text_and_tolerates_cents() -> None:
    assert values_match("  CENTRO   EJEMPLO ", "centro ejemplo")
    assert values_match(120.999, 121.0)
    assert not values_match(120.98, 121.0)


def test_evaluation_reports_matches_missing_and_mismatches() -> None:
    report = AnalysisReport(
        provider="content_understanding",
        analyzer_id="custom_invoice",
        duration_ms=100,
        documents=[
            ExtractedDocument(
                document_type="invoice",
                analyzer_id="custom_invoice",
                fields={
                    "SupplierName": ExtractedField("Proveedor S.L."),
                    "TotalAmount": ExtractedField(112.0),
                },
            )
        ],
    )
    ground_truth = {
        "fields": {
            "SupplierName": "proveedor s.l.",
            "InvoiceNumber": "F-1",
            "TotalAmount": 121.0,
        }
    }

    result = evaluate_report(report, ground_truth)

    assert result["matched"] == 1
    assert result["expected"] == 3
    assert result["accuracy"] == 0.3333
    assert result["missing"] == ["InvoiceNumber"]
    assert result["mismatched"] == [{"path": "TotalAmount", "expected": 121.0, "actual": 112.0}]
