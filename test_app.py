import pytest
from app import app  # استيراد تطبيق Flask
from unittest.mock import patch
import asyncio
import json
import httpx

@pytest.fixture
def client():
    """تهيئة عميل الاختبار في Flask"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# 1. اختبار تحميل الصفحة الرئيسية

def test_homepage(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Our Web App" in response.data.decode("utf-8")

# 2. اختبار مسار غير صالح (404)

def test_404(client):
    response = client.get("/invalid-route")
    assert response.status_code == 404
    assert b"Oops! The page you're looking for doesn't exist." in response.data

# 3. اختبار بيانات أداء التطبيق

def test_app_performance(client):
    response = client.get("/app-performance")
    assert response.status_code == 200
    assert b"App Memory Usage" in response.data

# 4. اختبار إدارة الجلسات

def test_session_management(client):
    with client.session_transaction() as session:
        session['user'] = 'test_user'
    response = client.get("/")
    assert session['user'] == 'test_user'

# 5. اختبار تسجيل الأخطاء

def test_error_logging(client, caplog):
    with patch("app.psutil.Process.memory_info", side_effect=Exception("Test Error")):
        response = client.get("/app-performance")
        assert response.status_code == 500
        assert "Unhandled error: Test Error" in caplog.text

# 6. اختبار الأداء باستخدام pytest-benchmark

def test_response_time(client, benchmark):
    result = benchmark(client.get, "/app-performance")
    assert result.status_code == 200

# 7. اختبار الطلبات المتزامنة باستخدام asyncio
@pytest.mark.asyncio
async def test_concurrent_requests():
    async with httpx.AsyncClient() as client:
        async def fetch():
            response = await client.get("http://localhost:5050/app-performance")
            return response

        tasks = [fetch() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        for response in responses:
            assert response.status_code == 200

# 8. اختبار تحليل الطلبات ومعالجة الإدخال

def test_request_analysis(client):
    malicious_payload = {"request_input": "<script>alert('XSS')</script>", "method": "GET"}
    response = client.post("/request-analysis", data=malicious_payload)
    assert response.status_code in [400, 422]
    assert b"No request input provided" not in response.data

# 9. اختبار نقطة التحقق من الصحة (Health Check)

def test_health_check(client):
    response = client.get("/user-activity")
    assert response.status_code == 200
    assert b"User Activity" in response.data

# 10. اختبار محاكاة تبعيات خارجية

def test_mock_external_dependency(client, mocker):
    # Create a mock object with an rss attribute
    mock_memory_info = mocker.Mock()
    mock_memory_info.rss = 1000000  # Set RSS to 1MB

    # Patch psutil.Process.memory_info() to return the mock object
    mocker.patch("app.psutil.Process.memory_info", return_value=mock_memory_info)

    response = client.get("/app-performance")
    assert response.status_code == 200

# 11. Test clearing user activity log
def test_clear_user_activity(client):
    response = client.post("/clear-log")
    assert response.status_code == 200
    assert response.json["success"] is True

# 12. Test clearing session
def test_clear_session(client):
    with client.session_transaction() as session:
        session["user"] = "test_user"
    response = client.post("/clear-session")
    assert response.status_code == 200
    assert response.json["success"] is True

# 13. Test session storage and retrieval
def test_session_storage(client):
    with client.session_transaction() as session:
        session["username"] = "test_user"
    response = client.get("/")
    with client.session_transaction() as session:
        assert session.get("username") == "test_user"

# 14. Test serving static files
def test_static_files(client):
    response = client.get("/static/test.txt")
    assert response.status_code in [200, 404]  # May return 404 if file doesn't exist


def test_request_analysis_get(client, requests_mock):
    url = "https://example.com"
    requests_mock.get(url, text="Mocked GET response", status_code=200)

    response = client.post("/request-analysis", data={"request_input": url, "method": "GET"})
    response_data = response.get_json()

    assert response.status_code == 200
    assert response_data["method"] == "GET"
    assert response_data["status_code"] == 200
    assert "Mocked GET response" in response_data["response"]

def test_request_analysis_post(client, requests_mock):
    url = "https://example.com"
    requests_mock.post(url, text="Mocked POST response", status_code=201)

    response = client.post("/request-analysis", data={"request_input": url, "method": "POST"})
    response_data = response.get_json()

    assert response.status_code == 201
    assert response_data["method"] == "POST"
    assert response_data["status_code"] == 201
    assert "Mocked POST response" in response_data["response"]

def test_request_analysis_no_input(client):
    response = client.post("/request-analysis", data={})
    response_data = response.get_json()

    assert response.status_code == 400
    assert response_data["error"] == "No request input provided"

def test_request_analysis_invalid_method(client):
    url = "https://example.com"
    response = client.post("/request-analysis", data={"request_input": url, "method": "PUT"})
    response_data = response.get_json()

    assert response.status_code == 400
    assert response_data["error"] == "Unsupported method: PUT"


