
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_invalid_date_range():
    response = client.get(
        "/availability",
        params={
            "check_in": "2030-12-15",
            "check_out": "2030-12-10",
            "room_type": "Deluxe"
        }
    )
    assert response.status_code == 400


def test_booking_and_capacity():
    dates = {
        "room_type": "Deluxe",
        "check_in": "2031-01-10",
        "check_out": "2031-01-12"
    }

    for customer in ["Test Rahul", "Test Priya"]:
        response = client.post(
            "/reservations",
            json={"customer_name": customer, **dates}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "confirmed"

    response = client.post(
        "/reservations",
        json={"customer_name": "Test Amit", **dates}
    )
    assert response.status_code == 409

