import requests
import argparse
import sys
import time
import json
import uuid
import random

from pymongo import MongoClient


class CouchDB:

    def __init__(self, _host, _port, _records):
        self._host = _host
        self._port = _port
        self._collection_name = 'test_envoxy_benchmark_{}'.format(str(uuid.uuid4()).replace('-', ''))
        self._records = _records
        self._field11_random_values = []
        self._headers = {
            'Content-Type': 'application/json'
        }
        self._feed_database()
        self._find_test()

    def _feed_database(self):

        _resp = requests.put(self._uri(), headers=self._headers)
        
        for i in range(self._records):

            _field11_random_value = uuid.uuid4()

            self._field11_random_values.append('{}'.format(_field11_random_value))
            self._field11_random_values.append('{}'.format(uuid.uuid4()))
            
            _resp = requests.post(self._uri(), headers=self._headers, json={
                "field00": '{}'.format(uuid.uuid4()),
                "field01": '{}'.format(uuid.uuid4()),
                "field02": '{}'.format(uuid.uuid4()),
                "field03": '{}'.format(uuid.uuid4()),
                "field04": '{}'.format(uuid.uuid4()),
                "field05": '{}'.format(uuid.uuid4()),
                "field06": '{}'.format(uuid.uuid4()),
                "field07": '{}'.format(uuid.uuid4()),
                "field08": '{}'.format(uuid.uuid4()),
                "field09": '{}'.format(uuid.uuid4()),
                "field10": '{}'.format(random.choice(['test0', 'test1', 'test2', 'test3'])),
                "field11": '{}'.format(_field11_random_value),
                "field12": '{}'.format(uuid.uuid4()),
                "field13": '{}'.format(uuid.uuid4()),
                "field14": '{}'.format(uuid.uuid4()),
                "field15": '{}'.format(uuid.uuid4()),
                "field16": '{}'.format(uuid.uuid4()),
                "field17": '{}'.format(uuid.uuid4()),
                "field18": '{}'.format(uuid.uuid4()),
                "field19": '{}'.format(uuid.uuid4()),
                "field20": '{}'.format(uuid.uuid4())
            })

            if _resp.status_code != 200:
                print('>>> Error!!! {}'.format(_resp.text))

    def _uri(self):
        return 'http://{}:{}/{}'.format(self._host, self._port, self._collection_name)

    def _find_test(self):
        print('Getting the CouchDB result from: {}: '.format(self._collection_name))
        
        for i in range(self._records):
            _resp = requests.post('{}/find'.format(self._uri()), headers=self._headers, json={
                "selector": {
                    "field10": {
                        "$eq": "test2"
                    },
                    "field11": {
                        "$in": [
                            random.choice(self._field11_random_values), 
                            random.choice(self._field11_random_values), 
                            random.choice(self._field11_random_values), 
                            random.choice(self._field11_random_values)
                        ]
                    }
                },
                "limit": 999999999999
            })

            if _resp.status_code == 200:
                print(_resp.json()['docs'])
            else:
                print('>>> Error!!! {}'.format(_resp.text))


class MongoDB:

    def __init__(self, _host, _port, _records):
        self._host = _host
        self._port = _port
        self._records = _records
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

    _database = args.database

    start_time = time.time()
    
    if _database == 'couchdb':
        CouchDB(args.host, args.port, args.records)
    elif _database == 'mongodb':
        MongoDB(args.host, args.port, args.records)
    else:
        print('Unsupported database: {}'.format(_database))
        return

    print('--- %s seconds ---' % (time.time() - start_time))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Benchmark NoSQL Databases Script')
    parser.add_argument('--host', type=str, required=True, metavar='127.0.0.1', help='Database Host')
    parser.add_argument('--port', type=int, required=True, metavar=5984, help='Database Port')
    parser.add_argument('--database', type=str, required=True, metavar='couchdb|mongodb', help='Kind of database')
    parser.add_argument('--records', type=int, required=True, metavar='couchdb|mongodb', help='Amount of records to be generated in the test')
    
    _args = parser.parse_args()

    main(_args)

