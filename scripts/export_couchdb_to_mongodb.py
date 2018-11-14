import requests
import argparse
import sys
import time
import json

from pymongo import MongoClient


class CouchDB:

    def __init__(self, _host, _port):
        self._host = _host
        self._port = _port

    def uri(self, _database):
        return 'http://{}:{}/{}/_find'.format(self._host, self._port, _database)

    def find_all(self, _database):
        print('Getting the CouchDB result from: {}: '.format(_database))
        _resp = requests.post(self.uri(_database), json={
            "selector": {
                "_id": {
                    "$gt": None
                }
            },
            "limit": 999999999999
        })

        if _resp.status_code == 200:
            return _resp.json()['docs']
        else:
            return []


class MongoDB:

    def __init__(self, _host, _port):
        self._host = _host
        self._port = _port
        self._client = MongoClient(self.uri())

    def uri(self):
        return 'mongodb://{}:{}/'.format(self._host, self._port)

    def import_database(self, _database_name, _docs):

        try:
            _dbase_name, _collection_name = _database_name.split('_')
        except Exception as e:
            print('\nDatabase {} ignored!!!'.format(_database_name))
            return

        _db = self._client[_dbase_name]

        _collection = _db[_collection_name]
        _collection.drop()

        print('>>> Exporting from CouchDB "{}" and importing to MongoDB in "{}.{}": '.format(_database_name, _dbase_name, _collection_name), end='')

        for _doc in _docs:

            print('.', end='')
            sys.stdout.flush()

            try:
                _collection.insert_one(_doc)
            except Exception as e:

                if '$' in str(e):
                    try:
                        _collection.insert_one(json.loads(json.dumps(_doc).replace('{"$', '{"')))
                    except Exception as e1:
                        print('\nError: {} while trying to insert this object: {}'.format(e, _doc))
                else:
                    print('\nError: {} while trying to insert this object: {}'.format(e, _doc))

        print(' OK!')


def main(args):

    _databases = args.databases.replace('"', '').strip().split(',')

    if 'muzzley_migrations' in _databases:
        _databases.remove('muzzley_migrations')

    _source = CouchDB(args.couchdb_source_host, args.couchdb_source_port)
    _target = MongoDB(args.mongodb_target_host, args.mongodb_target_port)

    start_time = time.time()

    for _database in _databases:
        print('Exporting and importing: {}: '.format(_database))
        _target.import_database(_database, _source.find_all(_database))

    print('--- %s seconds ---' % (time.time() - start_time))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Export CouchDB to MongoDB Script')
    parser.add_argument('--couchdb-source-host', type=str, required=True, metavar='127.0.0.1', help='CouchDB Host')
    parser.add_argument('--couchdb-source-port', type=int, required=True, metavar=5984, help='CouchDB Port')
    parser.add_argument('--mongodb-target-host', type=str, required=True, metavar='127.0.0.1', help='CouchDB Host')
    parser.add_argument('--mongodb-target-port', type=int, required=True, metavar=27017, help='CouchDB Port')
    parser.add_argument('--databases', type=str, required=True, metavar='a,b,c', help='CouchDB databases to be exported')
    
    _args = parser.parse_args()

    main(_args)

