import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# 1. SETUP AGGRESSIVE MOCKING for heavy ML dependencies
# This must happen before ANY app imports
sys.modules["tensorflow"] = MagicMock()
sys.modules["tensorflow.keras"] = MagicMock()
sys.modules["tensorflow.keras.models"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["mlflow"] = MagicMock()
sys.modules["joblib"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["shap"] = MagicMock()
sys.modules["scipy.cluster"] = MagicMock()
sys.modules["shap._explanation"] = MagicMock()
sys.modules["matplotlib"] = MagicMock()
sys.modules["matplotlib.pyplot"] = MagicMock()

# Setup paths
sys.path.append(os.getcwd())

# 2. MOCK DATA MODELS (To avoid SQLAlchemy Metadata conflicts)
# We define dummy classes that look like SQLAlchemy models but don't register with Base
class MockUser:
    id = 1
    streak_count = 5
    email = "test@example.com"
    github_username = "testuser"
    github_token = "token"
    career_profile = MagicMock()

class MockRiskSnapshot:
    # 1. Class-level attribute for Query Construction (handles .desc())
    risk_score = MagicMock()
    user_id = MagicMock()
    recorded_at = MagicMock()

    def __init__(self, risk_score_val=50):
         # 2. Instance-level attribute for Data Access
        self.risk_score = risk_score_val
        self.user_id = 1
        self.recorded_at = datetime.utcnow()

# Inject these mocks into sys.modules so imports in career_engine pick them up
mock_user_module = MagicMock()
mock_user_module.User = MockUser
sys.modules["app.db.models.user"] = mock_user_module

mock_analytics_module = MagicMock()
mock_analytics_module.RiskSnapshot = MockRiskSnapshot
sys.modules["app.db.models.analytics"] = mock_analytics_module

mock_career_module = MagicMock()
mock_career_module.CareerProfile = MagicMock()
mock_career_module.LearningPlan = MagicMock()
sys.modules["app.db.models.career"] = mock_career_module

mock_ml_risk_log_module = MagicMock()
mock_ml_risk_log_module.MLRiskLog = MagicMock()
sys.modules["app.db.models.ml_risk_log"] = mock_ml_risk_log_module


# 3. IMPORT SERVICES
# Now it is safe to import services
from app.services.audit_service import audit_service
# We import career_engine inside a patch block to mock its internal dependencies
with patch.dict(sys.modules, {
    "app.ml.shap_explainer": MagicMock(),
    "app.services.counterfactual_engine": MagicMock(),
    "app.ml.risk_forecast_model": MagicMock(),
    "app.ml.lstm_risk_production": MagicMock(),
    "app.ml.feature_store": MagicMock(),
    "app.services.social_harvester": MagicMock(), # Mock to avoid httpx/PyGithub issues
    "app.services.growth_engine": MagicMock(),
    "app.services.mentor_engine": MagicMock(),
    "app.services.benchmark_engine": MagicMock(),
    "app.services.team_health_engine": MagicMock(),
    "app.services.alert_engine": MagicMock(),
}):
    from app.services.career_engine import career_engine

def test_audit_service():
    print("Testing AuditService...")
    db = MagicMock()

    # Test log_event
    success = audit_service.log_event(db, "TEST_EVENT", "Test Details", "INFO", 1)
    if success:
        print("✅ log_event success")
    else:
        print("❌ log_event failed")

    # Verify db.add was called
    if db.add.called:
         print("✅ db.add called")
    else:
         print("❌ db.add NOT called")

    # Test get_compliance_summary
    # Mock query chain
    mock_query = db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.count.return_value = 5
    mock_entry = MagicMock()
    mock_entry.timestamp = datetime.utcnow()
    mock_filter.order_by.return_value.first.return_value = mock_entry

    summary = audit_service.get_compliance_summary(db, 1)
    if summary["total_events"] == 5 and summary["status"] == "ACTIVE":
        print("✅ get_compliance_summary success")
    else:
        print(f"❌ get_compliance_summary failed: {summary}")

    # Test check_system_integrity
    mock_filter.count.return_value = 10
    integrity = audit_service.check_system_integrity(db)
    if integrity["status"] == "HEALTHY":
        print("✅ check_system_integrity success")
    else:
        print(f"❌ check_system_integrity failed: {integrity}")

def test_career_engine_integration():
    print("\nTesting CareerEngine Integration...")
    db = MagicMock()
    user = MockUser()

    # Mock RiskSnapshot query for risk spike detection
    # Scenario: Last risk was 50, current forecast is 80 (Delta 30 > 15) -> Should trigger log
    last_snapshot = MockRiskSnapshot(risk_score_val=50)

    # Mock DB Query Chain for Snapshots
    # career_engine calls: db.query(RiskSnapshot).filter(...).order_by(...).limit(5).all()
    mock_query = db.query.return_value
    # Mocking the filter call is tricky because it's called with an expression (RiskSnapshot.user_id == user.id)
    # So we mock the return value of filter regardless of arguments
    mock_filter = mock_query.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_limit = mock_order.limit.return_value
    mock_limit.all.return_value = [last_snapshot]

    # Mock CareerEngine methods to isolate analyze logic
    # We mock the internal methods to avoid complex logic execution
    career_engine.forecast_career_risk = MagicMock(return_value={"risk_score": 80, "risk_level": "HIGH"})
    career_engine._calculate_skill_confidence = MagicMock(return_value={})
    career_engine.analyze_skill_alignment = MagicMock(return_value=[])
    career_engine.should_enable_accelerator = MagicMock(return_value=False)

    # Mock audit_service (imported in career_engine)
    with patch("app.services.career_engine.audit_service") as mocked_audit_service:
        mocked_audit_service.get_compliance_summary.return_value = {"status": "ACTIVE"}
        mocked_audit_service.check_system_integrity.return_value = {"status": "HEALTHY"}

        # Run analyze
        result = career_engine.analyze(db, {}, {}, {}, {}, user)

        # Verify Risk Spike Logging
        # Expected: risk_delta = 80 - 50 = 30 > 15 -> log_event called
        mocked_audit_service.log_event.assert_called_with(
            db,
            event_type="RISK_SPIKE",
            severity="WARNING",
            details="User risk spiked by 30 points (Previous: 50, Current: 80)",
            user_id=1
        )
        print("✅ Risk Spike logging verified")

        # Verify System Audit Data Injection
        if "system_audit" in result:
             print("✅ system_audit data present in result")
        else:
             print("❌ system_audit data MISSING in result")

if __name__ == "__main__":
    test_audit_service()
    test_career_engine_integration()
