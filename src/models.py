"""Validated domain models shared across the request-processing pipeline."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ClassificationState = Literal["matched", "out_of_scope", "unclear"]
PolicyStatus = Literal["متوافق", "عاجل ويتطلب موافقة", "مخالف", "خارج النطاق"]
ReviewStatus = Literal["بانتظار المراجعة", "تمت المراجعة"]
CommercialRegisterStatus = Literal["متوفر", "غير متوفر", "غير واضح"]


class DomainModel(BaseModel):
    """Strict base model for model output and deterministic application data."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ServiceDefinition(DomainModel):
    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    use_when: str = Field(min_length=1)
    exclusions: str = Field(min_length=1)
    min_days: int | None = Field(default=None, ge=1)
    max_days: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_duration_range(self) -> "ServiceDefinition":
        if (self.min_days is None) != (self.max_days is None):
            raise ValueError("service duration must provide both minimum and maximum days")
        if self.min_days is not None and self.max_days is not None:
            if self.max_days < self.min_days:
                raise ValueError("service maximum duration cannot be below its minimum")
        return self


class ReferenceData(DomainModel):
    services: tuple[ServiceDefinition, ...]
    global_min_execution_days: int = Field(ge=1)
    raw_policy_text: str = Field(min_length=1)
    raw_template_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_service_ids(self) -> "ReferenceData":
        ids = [service.id for service in self.services]
        if len(ids) != len(set(ids)):
            raise ValueError("service IDs must be unique")
        return self


class AIAnalysis(DomainModel):
    organization_name: str | None = None
    contact_name: str | None = None
    contact_role: str | None = None
    contact_method: str | None = None
    need_summary: str = Field(min_length=1)
    requested_deadline_text: str | None = None
    requested_working_days: int | None = Field(default=None, ge=1)
    commercial_register_text: str | None = None
    primary_service_id: int | None = Field(default=None, ge=1)
    secondary_service_id: int | None = Field(default=None, ge=1)
    classification_state: ClassificationState
    classification_reason: str = Field(min_length=1)

    @field_validator(
        "organization_name",
        "contact_name",
        "contact_role",
        "contact_method",
        "requested_deadline_text",
        "commercial_register_text",
        mode="before",
    )
    @classmethod
    def normalize_unknown_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        unknown_markers = {
            "",
            "null",
            "unknown",
            "غير معروف",
            "غير مذكور",
            "غير محدد",
            "غير واضح",
        }
        return None if normalized.lower() in unknown_markers else normalized

    @model_validator(mode="after")
    def validate_service_selection(self) -> "AIAnalysis":
        if self.classification_state == "matched" and self.primary_service_id is None:
            raise ValueError("a matched analysis requires a primary service")
        if self.classification_state != "matched" and (
            self.primary_service_id is not None or self.secondary_service_id is not None
        ):
            raise ValueError("unclear and out-of-scope analyses cannot select services")
        if self.primary_service_id == self.secondary_service_id and self.primary_service_id is not None:
            raise ValueError("primary and secondary services must be different")
        if self.secondary_service_id is not None and self.primary_service_id is None:
            raise ValueError("a secondary service requires a primary service")
        return self


def validate_analysis_service_ids(
    analysis: AIAnalysis, services: tuple[ServiceDefinition, ...] | list[ServiceDefinition]
) -> AIAnalysis:
    """Reject model-selected IDs that do not exist in the current catalog."""

    allowed_ids = {service.id for service in services}
    selected_ids = {
        service_id
        for service_id in (analysis.primary_service_id, analysis.secondary_service_id)
        if service_id is not None
    }
    invalid_ids = selected_ids - allowed_ids
    if invalid_ids:
        invalid_text = ", ".join(str(service_id) for service_id in sorted(invalid_ids))
        raise ValueError(f"service IDs are not in the current catalog: {invalid_text}")
    return analysis


class PolicyResult(DomainModel):
    status: PolicyStatus
    alerts: list[str] = Field(default_factory=list)
    next_step: str = Field(min_length=1)


class InternalSummary(DomainModel):
    """Fields follow the supplied Arabic output template order."""

    organization_name: str
    contact_person_and_role: str
    contact_method: str
    need_summary: str
    primary_service: str
    secondary_service: str
    commercial_register: CommercialRegisterStatus
    requested_deadline: str
    policy_status: PolicyStatus
    missing_data: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    next_step: str
    review_status: ReviewStatus = "بانتظار المراجعة"


class ProcessedRequest(DomainModel):
    request_id: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    input_source: str = Field(min_length=1)
    raw_request: str = Field(min_length=1)
    analysis: AIAnalysis
    summary: InternalSummary
