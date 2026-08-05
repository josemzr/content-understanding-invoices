from __future__ import annotations

from copy import deepcopy
from typing import Any

INVOICE_ANALYZER_ID = "custom_invoice"
DELIVERY_NOTE_ANALYZER_ID = "custom_delivery_note"
ROUTER_ANALYZER_ID = "document_router"


def _field(
    field_type: str,
    description: str,
    *,
    estimate_source_and_confidence: bool = True,
) -> dict[str, Any]:
    return {
        "type": field_type,
        "method": "extract",
        "description": description,
        "estimateSourceAndConfidence": estimate_source_and_confidence,
    }


def _line_items(properties: dict[str, dict[str, Any]], description: str) -> dict[str, Any]:
    return {
        "type": "array",
        "method": "extract",
        "description": description,
        "estimateSourceAndConfidence": True,
        "items": {"type": "object", "properties": properties},
    }


def _document_analyzer(
    analyzer_id: str,
    description: str,
    fields: dict[str, dict[str, Any]],
    completion_model: str,
    embedding_model: str,
) -> dict[str, Any]:
    return {
        "analyzerId": analyzer_id,
        "description": description,
        "baseAnalyzerId": "prebuilt-document",
        "models": {
            "completion": completion_model,
            "embedding": embedding_model,
        },
        "config": {
            "returnDetails": True,
            "enableOcr": True,
            "enableLayout": True,
            "enableFormula": False,
            "estimateFieldSourceAndConfidence": True,
            "tableFormat": "html",
        },
        "fieldSchema": {"fields": fields},
        "tags": {"sample": "invoice-delivery-note-processing", "version": "1"},
    }


def invoice_analyzer(completion_model: str, embedding_model: str) -> dict[str, Any]:
    fields = {
        "SupplierName": _field("string", "Razón social del proveedor que emite la factura."),
        "SupplierTaxId": _field("string", "NIF, CIF o identificador fiscal del proveedor."),
        "InvoiceNumber": _field("string", "Número único de la factura."),
        "InvoiceDate": _field("date", "Fecha de emisión de la factura."),
        "PurchaseOrderNumber": _field(
            "string", "Número de pedido u orden de compra asociado, si aparece."
        ),
        "RecipientName": _field(
            "string", "Nombre del cliente, centro o establecimiento al que se factura."
        ),
        "RecipientAddress": _field(
            "string", "Dirección de facturación o entrega del destinatario."
        ),
        "Currency": _field("string", "Código o símbolo de la moneda de la factura."),
        "Subtotal": _field("number", "Base imponible total antes de impuestos."),
        "TaxAmount": _field("number", "Importe total de impuestos."),
        "TotalAmount": _field("number", "Importe total final de la factura."),
        "PaymentDueDate": _field("date", "Fecha límite de pago, si aparece."),
        "LineItems": _line_items(
            {
                "Description": _field("string", "Descripción literal del producto o servicio."),
                "SupplierItemCode": _field(
                    "string", "Código, referencia o SKU asignado por el proveedor."
                ),
                "Quantity": _field("number", "Cantidad facturada."),
                "UnitOfMeasure": _field("string", "Unidad de medida de la cantidad."),
                "UnitPrice": _field("number", "Precio por unidad antes de impuestos."),
                "TaxRate": _field("number", "Porcentaje de impuesto aplicado a la línea."),
                "Amount": _field("number", "Importe total de la línea."),
            },
            "Líneas de productos o servicios facturados, conservando el orden del documento.",
        ),
    }
    return _document_analyzer(
        INVOICE_ANALYZER_ID,
        "Extrae los campos necesarios para registrar facturas en un sistema de gestión.",
        fields,
        completion_model,
        embedding_model,
    )


def delivery_note_analyzer(completion_model: str, embedding_model: str) -> dict[str, Any]:
    fields = {
        "SupplierName": _field("string", "Razón social del proveedor que entrega la mercancía."),
        "SupplierTaxId": _field("string", "NIF, CIF o identificador fiscal del proveedor."),
        "DeliveryNoteNumber": _field("string", "Número único del albarán."),
        "DeliveryDate": _field("date", "Fecha en la que se realizó la entrega."),
        "PurchaseOrderNumber": _field(
            "string", "Número de pedido u orden de compra asociado, si aparece."
        ),
        "RecipientName": _field(
            "string", "Nombre de la entidad, centro o establecimiento receptor."
        ),
        "RecipientAddress": _field("string", "Dirección donde se entrega la mercancía."),
        "ReceiverName": _field("string", "Nombre de la persona que recibe o firma el albarán."),
        "TotalPackages": _field("integer", "Número total de bultos entregados, si aparece."),
        "Notes": _field("string", "Incidencias, reservas u observaciones manuscritas o impresas."),
        "LineItems": _line_items(
            {
                "Description": _field("string", "Descripción literal del producto entregado."),
                "SupplierItemCode": _field(
                    "string", "Código, referencia o SKU asignado por el proveedor."
                ),
                "QuantityDelivered": _field("number", "Cantidad efectivamente entregada."),
                "UnitOfMeasure": _field("string", "Unidad de medida de la cantidad entregada."),
                "LotNumber": _field("string", "Número de lote, si aparece."),
                "ExpirationDate": _field("date", "Fecha de caducidad, si aparece."),
            },
            "Líneas de mercancía entregada, conservando el orden del documento.",
        ),
    }
    return _document_analyzer(
        DELIVERY_NOTE_ANALYZER_ID,
        "Extrae albaranes de proveedores con formatos variables para un sistema de gestión.",
        fields,
        completion_model,
        embedding_model,
    )


def router_analyzer(completion_model: str) -> dict[str, Any]:
    return {
        "analyzerId": ROUTER_ANALYZER_ID,
        "description": "Clasifica facturas y albaranes y los envía a su analizador específico.",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": completion_model},
        "config": {
            "enableSegment": False,
            "omitContent": True,
            "contentCategories": {
                "invoice": {
                    "description": (
                        "Factura que solicita el pago de bienes o servicios e incluye importes, "
                        "impuestos, total y normalmente un número de factura."
                    ),
                    "analyzerId": INVOICE_ANALYZER_ID,
                },
                "delivery_note": {
                    "description": (
                        "Albarán, nota de entrega o delivery note que acredita mercancía entregada "
                        "y normalmente no solicita el pago ni contiene total de factura."
                    ),
                    "analyzerId": DELIVERY_NOTE_ANALYZER_ID,
                },
                "other": {
                    "description": "Documento que no es una factura ni un albarán.",
                },
            },
        },
        "tags": {"sample": "invoice-delivery-note-processing", "version": "1"},
    }


def all_analyzers(completion_model: str, embedding_model: str) -> list[dict[str, Any]]:
    return [
        deepcopy(invoice_analyzer(completion_model, embedding_model)),
        deepcopy(delivery_note_analyzer(completion_model, embedding_model)),
        deepcopy(router_analyzer(completion_model)),
    ]
