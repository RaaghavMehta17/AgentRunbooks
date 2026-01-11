from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import IncidentLink


def link_pd_to_jira(run_id: str, pd_incident_id: str, jira_issue_key: str) -> None:
    """Link a PagerDuty incident to a Jira issue for a run."""
    with SessionLocal() as db:
        # Check if link already exists
        stmt = (
            select(IncidentLink)
            .where(IncidentLink.run_id == run_id)
            .where(IncidentLink.pd_incident_id == pd_incident_id)
            .where(IncidentLink.jira_issue_key == jira_issue_key)
        )
        existing = db.scalars(stmt).first()
        if existing:
            return  # Already linked

        link = IncidentLink(
            run_id=run_id,
            pd_incident_id=pd_incident_id,
            jira_issue_key=jira_issue_key,
        )
        db.add(link)
        db.commit()


def get_incident_links(run_id: str) -> list[dict[str, str | None]]:
    """Get all incident links for a run."""
    with SessionLocal() as db:
        stmt = select(IncidentLink).where(IncidentLink.run_id == run_id)
        links = db.scalars(stmt).all()
        return [
            {
                "pd_incident_id": link.pd_incident_id,
                "jira_issue_key": link.jira_issue_key,
            }
            for link in links
        ]


async def autolink_comments(pd_incident_id: str, jira_issue_key: str) -> None:
    """Auto-link comments between PagerDuty and Jira (optional)."""
    # This would require fetching comments from both systems and cross-posting
    # For now, this is a placeholder that can be extended
    pass

