from typing import List, Optional

from pydantic import BaseModel, computed_field


class AlertAction(BaseModel):
    id: str
    description: str
    owner_role: str
    due_within_hours: int


class AlertScope(BaseModel):
    facilities: list[str] = []
    lanes: list[str] = []
    shipments: list[str] = []


class AlertImpactAssessment(BaseModel):
    time_risk_days: float | None = None
    revenue_at_risk: float | None = None
    customers_affected: list[str] = []
    qualitative_impact: list[str] = []


class AlertDiagnostics(BaseModel):
    """Diagnostic information for alert audit and debugging."""
    link_confidence: dict[str, float] = {}
    link_provenance: dict[str, str] = {}
    shipments_total_linked: int = 0
    shipments_truncated: bool = False
    impact_score: int = 0
    impact_score_breakdown: list[str] = []


class SentinelAlert(BaseModel):
    alert_id: str
    risk_type: str
    classification: int  # 0=Interesting, 1=Relevant, 2=Impactful (canonical field)
    status: str
    summary: str
    root_event_id: str
    scope: AlertScope
    impact_assessment: AlertImpactAssessment
    reasoning: list[str]
    recommended_actions: List[AlertAction]
    model_version: str = "sentinel-v1"
    confidence_score: Optional[float] = None
    diagnostics: Optional[AlertDiagnostics] = None
    
    # Backward compatibility: priority mirrors classification
    # DEPRECATED: Use classification instead. This field will be removed in a future version.
    @computed_field
    @property
    def priority(self) -> int:
        """
        Deprecated: Use classification instead.
        
        Returns classification value for backward compatibility.
        This field mirrors classification and will be removed in a future version.
        """
        return self.classification

