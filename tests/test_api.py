
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    # Entering TestClient context runs application startup.
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_invalid_date_range(client):
    response = client.get(
        "/availability",
        params={
            "check_in": "2030-12-15",
            "check_out": "2030-12-10",
            "room_type": "Deluxe"
        }
    )

    assert response.status_code == 400


def test_booking_and_capacity(client):
    dates = {
        "room_type": "Deluxe",
        "check_in": "2031-01-10",
        "check_out": "2031-01-12"
    }

    for customer in ["Test Rahul", "Test Priya"]:
        response = client.post(
            "/reservations",
            json={
                "customer_name": customer,
                **dates
            }
        )

        assert response.status_code == 201
        assert response.json()["status"] == "confirmed"

    response = client.post(
        "/reservations",
        json={
            "customer_name": "Test Amit",
            **dates
        }
    )

    assert response.status_code == 409
