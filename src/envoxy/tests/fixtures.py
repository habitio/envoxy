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
        "value": 30.5,
        "active": True,
        "created" : "2018-01-18T16:07:01.970+0000",
        "headers": "{\"Date\":\"Mon, 19 Aug 2019 10:16:21 UTC\",\"Server\":\"zapata RESTful server\",\"Vary\":\"Accept-Language,Accept-Encoding,X-Access-Token,Authorization,E-Tag\",\"X-Cid\":\"3c12ab6b-bfb0-40ff-b060-0892b985b473\",\"X-Status\":200}"
    }
