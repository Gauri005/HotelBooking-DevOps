import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

barrier = Barrier(2)

def book(customer):
    data = {
        "customer_name": customer,
        "room_type": "Suite",
        "check_in": "2035-06-10",
        "check_out": "2035-06-12"
    }

    barrier.wait()

    request = urllib.request.Request(
        "http://localhost:8000/reservations",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()

with ThreadPoolExecutor(max_workers=2) as executor:
    results = list(executor.map(book, ["Customer A", "Customer B"]))

for result in results:
    print("STATUS:", result[0])
    print("RESPONSE:", result[1])
    print("--------------------")

success = sum(1 for status, _ in results if status == 201)
conflict = sum(1 for status, _ in results if status == 409)

print("SUCCESSFUL BOOKINGS:", success)
print("CONFLICTED BOOKINGS:", conflict)

if success == 1 and conflict == 1:
    print("PASS: Concurrent booking protection works!")
else:
    print("CHECK REQUIRED: Expected exactly one 201 and one 409.")
