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
            "icon": "\ud83d\ude0a"
        },
        "features": None,
        "value": 30.5,
        "active": True,
        "created" : "2018-01-18T16:07:01.970+0000",
        "headers": "{\"Date\":\"Mon, 19 Aug 2019 10:16:21 UTC\",\"Server\":\"zapata RESTful server\",\"Vary\":\"Accept-Language,Accept-Encoding,X-Access-Token,Authorization,E-Tag\",\"X-Cid\":\"3c12ab6b-bfb0-40ff-b060-0892b985b473\",\"X-Status\":200}",
        "unique_id": "f3be455a-c287-11e9-9ce0-a45e60dbf675",
        "regex" : "^([a-zA-Z0-9_@:;./+*|-]+)$"
    }
