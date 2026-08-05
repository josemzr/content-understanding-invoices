from azure.ai.contentunderstanding.models import ArrayField, ObjectField, StringField
from azure.ai.documentintelligence.models import CurrencyValue, DocumentField

from invoice_demo.models import field_value, normalize_field


def test_content_understanding_nested_field_is_converted_to_plain_values() -> None:
    field = ArrayField(
        type="array",
        value_array=[
            ObjectField(
                type="object",
                value_object={
                    "Description": StringField(type="string", value_string="Café"),
                },
            )
        ],
        confidence=0.94,
    )

    normalized = normalize_field(field)

    assert normalized.value == [{"Description": "Café"}]
    assert normalized.confidence == 0.94


def test_document_intelligence_currency_is_normalized_to_amount() -> None:
    field = DocumentField(
        type="currency",
        value_currency=CurrencyValue(amount=121.0, currency_code="EUR"),
        confidence=0.98,
    )

    assert field_value(field) == 121.0
