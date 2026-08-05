from invoice_demo.config import Settings


def test_model_deployments_use_model_names_as_keys() -> None:
    settings = Settings(
        content_understanding_endpoint="https://example.services.ai.azure.com/",
        document_intelligence_endpoint=None,
        completion_model="gpt-5.2",
        completion_deployment="production-gpt",
        embedding_model="text-embedding-3-large",
        embedding_deployment="production-embedding",
    )

    assert settings.model_deployments() == {
        "gpt-5.2": "production-gpt",
        "text-embedding-3-large": "production-embedding",
    }
