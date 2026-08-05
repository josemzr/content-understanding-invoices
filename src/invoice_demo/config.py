from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    content_understanding_endpoint: str | None
    document_intelligence_endpoint: str | None
    completion_model: str
    completion_deployment: str | None
    embedding_model: str
    embedding_deployment: str | None

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            content_understanding_endpoint=os.getenv("CONTENTUNDERSTANDING_ENDPOINT"),
            document_intelligence_endpoint=os.getenv("DOCUMENTINTELLIGENCE_ENDPOINT"),
            completion_model=os.getenv("CU_COMPLETION_MODEL", "gpt-5.2"),
            completion_deployment=os.getenv("CU_COMPLETION_DEPLOYMENT"),
            embedding_model=os.getenv("CU_EMBEDDING_MODEL", "text-embedding-3-large"),
            embedding_deployment=os.getenv("CU_EMBEDDING_DEPLOYMENT"),
        )

    def require_content_understanding_endpoint(self) -> str:
        if not self.content_understanding_endpoint:
            raise ValueError(
                "Set CONTENTUNDERSTANDING_ENDPOINT before using Content Understanding."
            )
        return self.content_understanding_endpoint

    def require_document_intelligence_endpoint(self) -> str:
        if not self.document_intelligence_endpoint:
            raise ValueError(
                "Set DOCUMENTINTELLIGENCE_ENDPOINT before using Document Intelligence."
            )
        return self.document_intelligence_endpoint

    def model_deployments(self) -> dict[str, str] | None:
        deployments: dict[str, str] = {}
        if self.completion_deployment:
            deployments[self.completion_model] = self.completion_deployment
        if self.embedding_deployment:
            deployments[self.embedding_model] = self.embedding_deployment
        return deployments or None
