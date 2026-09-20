from io import BytesIO
from fastapi.testclient import TestClient
from app.main import app, reports

client = TestClient(app)


def setup_function() -> None:
    reports.clear()


def register_user(email: str = "userA@example.com", password: str = "password123") -> tuple[str, str]:
    response = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200
    data = response.json()
    return data["user"]["id"], data["access_token"]


def test_user_registration_and_password_hashing() -> None:
    user_id, token = register_user("userA@example.com", "secretpass")
    assert user_id.startswith("u_")
    assert token

    # Verify password in DB is hashed and not stored in plaintext
    user_in_db = reports.get_user_by_email("userA@example.com")
    assert user_in_db is not None
    assert user_in_db["password_hash"].startswith("pbkdf2_sha256$")
    assert "secretpass" not in user_in_db["password_hash"]

    # Duplicate registration should return 409 Conflict
    dup_res = client.post("/api/auth/register", json={"email": "userA@example.com", "password": "otherpassword"})
    assert dup_res.status_code == 409


def test_user_login() -> None:
    register_user("userA@example.com", "correctpassword")

    # Wrong password
    bad_res = client.post("/api/auth/login", json={"email": "userA@example.com", "password": "wrongpassword"})
    assert bad_res.status_code == 401

    # Correct password
    good_res = client.post("/api/auth/login", json={"email": "userA@example.com", "password": "correctpassword"})
    assert good_res.status_code == 200
    assert good_res.json()["access_token"]


def test_unauthenticated_requests_rejected() -> None:
    # Unauthenticated GET /api/reports
    res = client.get("/api/reports")
    assert res.status_code == 401

    # Unauthenticated GET /api/auth/me
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 401


def test_multi_user_data_isolation() -> None:
    # Setup User A and User B
    userA_id, tokenA = register_user("userA@example.com", "passwordA")
    userB_id, tokenB = register_user("userB@example.com", "passwordB")

    headersA = {"Authorization": f"Bearer {tokenA}"}
    headersB = {"Authorization": f"Bearer {tokenB}"}

    # User A creates a report
    repA_id = "r_reportA"
    reports.create({
        "id": repA_id,
        "user_id": userA_id,
        "filename": "A_Report.pdf",
        "source_type": "pdf",
        "patient_id": "p_demo",
        "status": "pending_review",
        "results": [{"raw_test_name": "Hemoglobin", "value": 13.5}],
    })

    # User B creates a report
    repB_id = "r_reportB"
    reports.create({
        "id": repB_id,
        "user_id": userB_id,
        "filename": "B_Report.pdf",
        "source_type": "pdf",
        "patient_id": "p_demo",
        "status": "pending_review",
        "results": [{"raw_test_name": "Glucose", "value": 95.0}],
    })

    # 1. User A lists reports -> sees ONLY A_Report.pdf
    resA_list = client.get("/api/reports", headers=headersA)
    assert resA_list.status_code == 200
    report_ids_A = [r["id"] for r in resA_list.json()]
    assert repA_id in report_ids_A
    assert repB_id not in report_ids_A

    # 2. User B lists reports -> sees ONLY B_Report.pdf
    resB_list = client.get("/api/reports", headers=headersB)
    assert resB_list.status_code == 200
    report_ids_B = [r["id"] for r in resB_list.json()]
    assert repB_id in report_ids_B
    assert repA_id not in report_ids_B

    # 3. User A attempts to access User B's report directly (CRITICAL SECURITY TEST)
    # GET extraction
    res_cross_ext = client.get(f"/api/reports/{repB_id}/extraction", headers=headersA)
    assert res_cross_ext.status_code == 404

    # GET source
    res_cross_src = client.get(f"/api/reports/{repB_id}/source", headers=headersA)
    assert res_cross_src.status_code == 404

    # GET source-file
    res_cross_file = client.get(f"/api/reports/{repB_id}/source-file", headers=headersA)
    assert res_cross_file.status_code == 404

    # POST confirm
    res_cross_confirm = client.post(
        f"/api/reports/{repB_id}/confirm",
        json={"results": [{"raw_test_name": "Glucose", "value": 99.0, "extraction_confidence": 0.9}]},
        headers=headersA,
    )
    assert res_cross_confirm.status_code == 404

    # 4. User A attempts to DELETE User B's report (CRITICAL SECURITY TEST)
    res_cross_del = client.delete(f"/api/reports/{repB_id}", headers=headersA)
    assert res_cross_del.status_code == 404

    # Verify B's report was NOT deleted
    res_b_verify = client.get(f"/api/reports/{repB_id}/extraction", headers=headersB)
    assert res_b_verify.status_code == 200
    assert res_b_verify.json()["filename"] == "B_Report.pdf"


def test_user_delete_own_record() -> None:
    user_id, token = register_user("user_del@example.com", "password123")
    headers = {"Authorization": f"Bearer {token}"}

    rep_id = "r_tobedeleted"
    reports.create({
        "id": rep_id,
        "user_id": user_id,
        "filename": "DeleteMe.pdf",
        "source_type": "pdf",
        "patient_id": "p_demo",
        "status": "pending_review",
        "results": [],
    })

    del_res = client.delete(f"/api/reports/{rep_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify it is gone
    get_res = client.get(f"/api/reports/{rep_id}/extraction", headers=headers)
    assert get_res.status_code == 404
