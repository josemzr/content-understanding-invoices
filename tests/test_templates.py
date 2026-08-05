from invoice_demo.templates import (
    DELIVERY_NOTE_ANALYZER_ID,
    INVOICE_ANALYZER_ID,
    ROUTER_ANALYZER_ID,
    all_analyzers,
)


def test_templates_create_two_extractors_and_router() -> None:
    analyzers = all_analyzers("gpt-5.2", "text-embedding-3-large")

    assert [item["analyzerId"] for item in analyzers] == [
        INVOICE_ANALYZER_ID,
        DELIVERY_NOTE_ANALYZER_ID,
        ROUTER_ANALYZER_ID,
    ]
    assert analyzers[0]["models"] == {
        "completion": "gpt-5.2",
        "embedding": "text-embedding-3-large",
    }


def test_router_targets_document_specific_analyzers() -> None:
    router = all_analyzers("gpt-5.2", "text-embedding-3-large")[-1]
    categories = router["config"]["contentCategories"]

    assert categories["invoice"]["analyzerId"] == INVOICE_ANALYZER_ID
    assert categories["delivery_note"]["analyzerId"] == DELIVERY_NOTE_ANALYZER_ID
    assert "analyzerId" not in categories["other"]
