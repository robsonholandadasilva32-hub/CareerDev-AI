import pytest
from datetime import datetime, timedelta
from app.db.models.governance import GovernanceLog
from app.db.models.user import User
from app.db.models.analytics import RiskSnapshot
from app.services.audit_service import audit_service
from app.services.career_engine import career_engine
from app.jobs.retention import cleanup_governance_logs
from app.db.session import SessionLocal, engine
from app.db.base import Base

@pytest.fixture
def db_session():
    # Setup DB tables
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    yield session
    session.close()

    # Teardown
    Base.metadata.drop_all(bind=engine)

def test_audit_service_log(db_session):
    log = audit_service.log(db_session, user_id=None, event="TEST_EVENT", details="Test details", severity="INFO")
    assert log.id is not None
    assert log.event_type == "TEST_EVENT"

    fetched = db_session.query(GovernanceLog).filter_by(id=log.id).first()
    assert fetched is not None
    assert fetched.details == "Test details"

def test_audit_service_read(db_session):
    audit_service.log(db_session, user_id=None, event="E1", details="D1")
    audit_service.log(db_session, user_id=None, event="E2", details="D2")

    logs = audit_service.get_recent_logs(db_session, limit=10)
    assert len(logs) == 2
    assert logs[0].event_type == "E2" # Descending order

def test_career_engine_risk_spike_detection(db_session, mocker):
    # Setup user
    user = User(email="test_spike@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    # Setup previous snapshot (Risk 10)
    prev_snapshot = RiskSnapshot(user_id=user.id, risk_score=10, recorded_at=datetime.utcnow() - timedelta(days=1))
    db_session.add(prev_snapshot)
    db_session.commit()

    # Mock dependencies
    mocker.patch("app.services.career_engine.social_harvester.get_metrics", return_value={"languages": {"Python": 1000}})
    mocker.patch("app.services.career_engine.benchmark_engine.compute", return_value={})
    mocker.patch("app.services.career_engine.growth_engine.generate_weekly_plan", return_value={"mode": "GROWTH"})
    mocker.patch("app.services.career_engine.mentor_engine.proactive_insights")
    mocker.patch("app.services.career_engine.counterfactual_engine.generate", return_value={})
    mocker.patch("app.services.career_engine.mentor_engine.proactive_from_counterfactual")
    mocker.patch("app.services.career_engine.mentor_engine.generate_multi_week_plan", return_value={})
    mocker.patch("app.services.career_engine.shap_explainer.explain_visual", return_value={})
    mocker.patch("app.services.career_engine.benchmark_engine.compute_team_org", return_value={})
    mocker.patch("app.services.career_engine.benchmark_engine.get_user_history", return_value=[])
    mocker.patch("app.services.career_engine.benchmark_engine.compute_team_health", return_value={})
    mocker.patch("app.services.career_engine.team_health_engine.team_burnout_risk", return_value={})
    mocker.patch("app.services.career_engine.team_health_engine.simulate_member_exit", return_value={})

    # Mock forecast to return 50 (Delta 40)
    mocker.patch.object(career_engine, "forecast_career_risk", return_value={
        "risk_score": 50,
        "risk_level": "MEDIUM",
        "summary": "Risk increased significantly.",
        "reasons": [],
        "rule_risk": 50,
        "ml_risk": 0
    })

    # Run analyze
    career_engine.analyze(db_session, {"Python": 1000}, {}, {"commits_last_30_days": 10}, {}, user)

    # Verify GovernanceLog created
    log = db_session.query(GovernanceLog).filter_by(event_type="RISK_SPIKE_DETECTED").first()
    assert log is not None
    assert log.user_id == user.id
    assert "from 10 to 50" in log.details

    # Verify NEW snapshot created
    snapshots = db_session.query(RiskSnapshot).filter_by(user_id=user.id).order_by(RiskSnapshot.recorded_at.desc()).all()
    assert len(snapshots) >= 2
    assert snapshots[0].risk_score == 50

def test_retention_job(db_session, mocker):
    # Create old log
    old_log = GovernanceLog(event_type="OLD", created_at=datetime.utcnow() - timedelta(days=91))
    db_session.add(old_log)

    # Create new log
    new_log = GovernanceLog(event_type="NEW", created_at=datetime.utcnow() - timedelta(days=1))
    db_session.add(new_log)
    db_session.commit()

    # Run cleanup
    cleanup_governance_logs(days=90)

    # Verify
    assert db_session.query(GovernanceLog).filter_by(event_type="OLD").count() == 0
    assert db_session.query(GovernanceLog).filter_by(event_type="NEW").count() == 1
