import json

from envoxy.tools.validate_models import validate_model_file


def test_validate_models_ok(tmp_path):
    p = tmp_path / 'model.json'
    # create a model with a datum that defines fields including required ones
    content = {
        'datums': [
            {'fields': {'id': {}, 'created': {}, 'updated': {}, 'href': {}, 'name': {}}}
        ]
    }
    p.write_text(json.dumps(content))

    errors = validate_model_file(p)
    assert errors == []


def test_validate_models_missing(tmp_path):
    p = tmp_path / 'model.json'
    content = {'datums': [ {'fields': {'id': {}, 'created': {}}} ] }
    p.write_text(json.dumps(content))

    errors = validate_model_file(p)
    assert len(errors) == 1
