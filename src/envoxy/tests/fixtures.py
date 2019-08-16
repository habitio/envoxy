import pytest

@pytest.fixture
def test_payload():

    return {
        "username": "",
        "password": "mysecretpassword",
        "application_ids": [ 1, 2, 3 ],
        "age": 40,
        "user": {
            "name": "John Doe",
        },
        "features": None,
        "value": 30.5
    }
