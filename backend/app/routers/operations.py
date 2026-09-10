from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Advisory, Alert, InstitutionalUser, MlPrediction, Plot, SatelliteData, SmsLog
from app.routers.alerts import _sync_alerts
from app.routers.institutional_auth import get_current_institutional_user
from app.utils.time import utc_now

router = APIRouter(prefix="/institutional/operations", tags=["institutional-operations"])


@router.get("/status")
def get_operations_status(
    state: str | None = None,
    district: str | None = None,
    current_user: InstitutionalUser = Depends(get_current_institutional_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return aggregate workflow health without exposing farmer message content."""
    query = db.query(Plot).join(Plot.farmer).filter(Plot.status == "active")
    if state:
        query = query.filter(Plot.farmer.has(state=state))
    if district:
        query = query.filter(Plot.farmer.has(district=district))
    plots = [plot for plot in query.all() if _plot_allowed(current_user, plot)]
    plot_ids = [plot.plot_id for plot in plots]

    _sync_alerts(db)
    advisories = db.query(Advisory).filter(Advisory.plot_id.in_(plot_ids)).all() if plot_ids else []
    predictions = db.query(MlPrediction).filter(MlPrediction.plot_id.in_(plot_ids)).all() if plot_ids else []
    alerts = [alert for alert in db.query(Alert).filter(Alert.plot_id.in_(plot_ids)).all()] if plot_ids else []
    observations = (
        db.query(SatelliteData)
        .filter(SatelliteData.plot_id.in_(plot_ids), SatelliteData.ingestion_status == "success")
        .all()
        if plot_ids
        else []
    )
    sms_logs = (
        db.query(SmsLog)
        .filter(SmsLog.farmer_id.in_([plot.farmer_id for plot in plots]))
        .all()
        if plots
        else []
    )
    recent_cutoff = utc_now() - timedelta(hours=24)

    ingestion = Counter(plot.data_status for plot in plots)
    sources = Counter(row.data_source for row in observations)
    provenance = Counter(
        "synthetic_demo" if row.quality_flag == "synthetic_demo" else "provider"
        for row in observations
    )
    delivery = Counter(log.delivery_status for log in sms_logs)
    lifecycle = Counter(alert.status for alert in alerts)
    recent_ingestion = sum(
        1 for plot in plots if _is_recent(plot.last_ingestion_at, recent_cutoff)
    )
    recent_predictions = sum(
        1 for prediction in predictions if _is_recent(prediction.predicted_at, recent_cutoff)
    )
    recent_advisories = sum(
        1 for advisory in advisories if _is_recent(advisory.created_at, recent_cutoff)
    )

    return {
        "scope": {"state": state, "district": district},
        "generated_at": utc_now().isoformat(),
        "plots": {
            "active": len(plots),
            "data_status": dict(ingestion),
            "ingested_last_24h": recent_ingestion,
            "successful_observations": len(observations),
            "by_source": dict(sources),
            "provenance": dict(provenance),
        },
        "processing": {
            "predictions_total": len(predictions),
            "predictions_last_24h": recent_predictions,
            "advisories_total": len(advisories),
            "advisories_last_24h": recent_advisories,
        },
        "alerts": {
            "total": len(alerts),
            "by_status": dict(lifecycle),
        },
        "delivery": {
            "total_messages": len(sms_logs),
            "by_status": dict(delivery),
            "delivered_rate_percent": round(
                (delivery.get("delivered", 0) / len(sms_logs)) * 100, 1
            ) if sms_logs else None,
        },
    }


def _plot_allowed(user: InstitutionalUser, plot: Plot) -> bool:
    if user.role == "admin":
        return True
    geography = user.assigned_geography or {}
    farmer = plot.farmer
    return (
        (not geography.get("states") or farmer.state in geography["states"])
        and (not geography.get("districts") or farmer.district in geography["districts"])
    )


def _is_recent(value: datetime | None, cutoff: datetime) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value >= cutoff
