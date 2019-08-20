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
            "alias": "李连杰",
            "icon": "\ud83d\ude0a",
            "email": "john-doe@gmail.com",
            "phone": "7362391957",
            "cellphone": "(875) 837-6945",
            "home": [59.29954, 169.92246],
            "work": { "latitude": 5, "longitude": 14 },
        },
        "features": None,
        "value": 30.5,
        "active": True,
        "created" : "2018-01-18T16:07:01.970+0000",
        "headers": "{\"Date\":\"Mon, 19 Aug 2019 11:11:11 UTC\",\"Server\":\"nginx server\",\"Vary\":\"Accept-Language,Accept-Encoding,X-Access-Token,E-Tag\",\"X-Status\":400}",
        "unique_id": "f3be455a-c287-11e9-9ce0-a45e60dbf675",
        "regex" : "^([a-zA-Z0-9_@:;./+*|-]+)$",
        "location": { "latitude": "5.18", "longitude": "14.21" },
        "hash": "0235et4vb81mvjjmpc3lnspl0doj45tx9aiixgqibdass",
        "website": "https://example.com",
        "sample_uri": "https://example.com/?level={level_id}&size={size}"
    }
