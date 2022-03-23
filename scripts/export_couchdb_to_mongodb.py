import re
import os
import time
import json
import ijson
import codecs
import asyncio
import decimal
import datetime
import requests
import argparse
import threading
import multiprocessing

from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import InvalidDocument

COUCHDB_TRANSFER_MODE_REMOTE_SERVER = 'remote-server'
COUCHDB_TRANSFER_MODE_DUMP_FILES = 'dump-files'

class EnvoxyJsonEncoder(json.JSONEncoder):
    
    def default(self, o):
        
        if isinstance(o, decimal.Decimal):
            return float(o)

        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        
        return super(EnvoxyJsonEncoder, self).default(o)

class CouchDB:

    def __init__(self, host, port, directory=None):
        self._host = host
        self._port = port
        self._mode = COUCHDB_TRANSFER_MODE_DUMP_FILES if directory else COUCHDB_TRANSFER_MODE_REMOTE_SERVER
        self._directory = directory
        self._limit = 1000 if not directory else 99999999999
        self._sessions = {}

    def uri(self, database=None):
        
        if database:
            return 'http://{}:{}/{}'.format(self._host, self._port, database)
        else:
            return 'http://{}:{}'.format(self._host, self._port)

    def get_or_create_session(self):

        _thread_id = threading.get_ident()
        
        if not self._sessions.get(_thread_id):
            self._sessions[_thread_id] = requests.session()
            print('>>> Creating new session for the thread: {}'.format(_thread_id))

        return self._sessions[_thread_id]

    def count_rows(self, database):

        if self._mode == COUCHDB_TRANSFER_MODE_DUMP_FILES:

            _filepath = f'{self._directory}/{database}.json'

            if os.path.isfile(_filepath):

                with codecs.open(f'{self._directory}/{database}.json', 'rt') as _file:

                    _items = ijson.items(_file, 'rows.item.doc._id')

                    return len(list((_item for _item in _items if _item.startswith('/v3'))))

            else:

                raise Exception(f'Error: File "{_filepath}" not found.')

        else:

            _session = self.get_or_create_session()

            print('>>> Getting the CouchDB rows count from: {}:'.format(database), end='')

            _resp = _session.post(f'{self.uri(database)}/_find', json={
                "selector": {
                    "_id": {
                        "$gt": None
                    }
                },
                "fields": ["_id"],
                "limit": 99999999
            })

            if _resp.status_code == 200:
                _size = len(_resp.json()['docs'])
                print(str(_size))
                return _size
            else:
                print('0')
                return 0


    def get_all_databases(self):

        _session = self.get_or_create_session()

        print('>>> Getting all CouchDB databases')

        _resp = _session.get(f'{self.uri()}/_all_dbs')

        if _resp.status_code == 200:
            return _resp.json()
        else:
            return []

    def find_all(self, database, index=0):

        if self._mode == COUCHDB_TRANSFER_MODE_DUMP_FILES:

            with codecs.open(f'{self._directory}/{database}.json', 'rt') as _file:

                _items = ijson.items(_file, 'rows.item.doc')
                
                return list((_item for _item in _items if _item.get('_id', '').startswith('/v3')))
        
        else:

            _session = self.get_or_create_session()

            print('>>> Getting the CouchDB result from: {} ({}:{})'.format(database, index*self._limit, (index*self._limit)+self._limit))

            _resp = _session.get(f'{self.uri(database)}/_all_docs?include_docs=true', json={
                "selector": {
                    "_id": {
                        "$gt": None
                    }
                },
                "skip": index*self._limit,
                "limit": self._limit
            })

            if _resp.status_code == 200:
                return _resp.json()['docs']
            else:
                return []

    def find_all_indexes(self, database):

        _session = self.get_or_create_session()

        print('>>> Getting the CouchDB indexes result from: {}'.format(database))

        _resp = _session.get(f'{self.uri(database)}/_index')

        if _resp.status_code == 200:
            return _resp.json()['indexes']
        else:
            return []

class MongoDB:

    def __init__(self, _host, _port):
        self._host = _host
        self._port = _port
        self._client = MongoClient(self.uri())

    def uri(self):
        return 'mongodb://{}:{}/'.format(self._host, self._port)

    @staticmethod
    def import_tables(collection, database_name, source, index):

        _docs = source.find_all(database_name, index=index)

        if _docs:

            _docs = json.loads(
                json.dumps(_docs, cls=EnvoxyJsonEncoder)\
                    .replace('{"$', '{"')
            )

            try:
                collection.insert_many(_docs, ordered=True)
            except InvalidDocument as _e:
                
                print('>>> Error: "{}" trying to insert again replacing the invalid dotted keys'.format(_e))

                _new_docs = []
                
                for _doc in _docs:
                    
                    _doc_str = json.dumps(_doc, cls=EnvoxyJsonEncoder)
                    
                    _matches = re.findall(r'("[^."]+[\.][^"]+"):', _doc_str)

                    if _matches:
                        
                        for _key in _matches:

                            _doc_str = _key.replace('.', '_').join(_doc_str.split(_key))

                        _new_docs.append(json.loads(_doc_str))
                    
                    else:

                        _new_docs.append(_doc)
                        
                try:
                    collection.insert_many(_new_docs, ordered=True)
                except InvalidDocument as _e:
                    print('>>> Error: "{}" after trying to insert again replacing dotted keys in the docs'.format(_e))
                    

    @staticmethod
    def create_indexes(collection, database_name, fields):

        if not fields:
            return
            
        print('>>> Creating index in {}: {}'.format(database_name, fields))
            
        collection.create_index(fields)

    async def import_database(self, database_name, source, max_workers):

        _index = 0

        try:
            _dbase_name, _collection_name = database_name.split('_')
        except Exception as e:
            print('\n>>> Database {} ignored!!!'.format(database_name))
            return

        _db = self._client[_dbase_name]

        _collection = _db[_collection_name]

        _collection.drop()

        print('>>> Exporting from CouchDB "{}" and importing to MongoDB in "{}.{}"'.format(database_name, _dbase_name, _collection_name))

        _row_count = source.count_rows(database_name)

        _tasks =  []

        with ThreadPoolExecutor(max_workers=max_workers) as _executor:
    
            _loop = asyncio.get_event_loop()

            while True:

                _tasks.append(
                    _loop.run_in_executor(
                        _executor,
                        self.import_tables,
                        *(_collection, database_name, source, _index)
                    )
                )

                if source._limit > _row_count or (_index * source._limit) > _row_count:
                    break

                _index += 1
        
            return await asyncio.gather(*_tasks)

    async def import_database_indexes(self, database_name, source, max_workers):

        try:
            _dbase_name, _collection_name = database_name.split('_')
        except Exception as e:
            print('\n>>> Database {} ignored!!!'.format(database_name))
            return

        _db = self._client[_dbase_name]

        _collection = _db[_collection_name]

        print('>>> Exporting from CouchDB "{}" indexes and importing to MongoDB in "{}.{}"'.format(database_name, _dbase_name, _collection_name))

        _indexes = source.find_all_indexes(database_name)

        if not _indexes:
            print('>>> No indexes found')
            return

        with ThreadPoolExecutor(max_workers=max_workers) as _executor:
    
            _loop = asyncio.get_event_loop()

            _tasks = []

            for _index in _indexes:

                _fields = [
                    (list(_item.keys())[0], ASCENDING if list(_item.values())[0] == 'asc' else DESCENDING) 
                        for _item in _index.get('def', {}).get('fields', [])
                        if list(_item.keys())[0] not in ['_id']
                ]

                _tasks.append(
                    _loop.run_in_executor(
                        _executor,
                        self.create_indexes,
                        *(_collection, database_name, _fields)
                    )
                )

            return asyncio.gather(*_tasks)

async def main(args):

    _dirty_databases = args.databases.replace('"', '').strip().split(',')

    _source = CouchDB(args.couchdb_source_host, args.couchdb_source_port, directory=args.source_directory)
    _target = MongoDB(args.mongodb_target_host, args.mongodb_target_port)

    if _dirty_databases[0] == 'all':
        _dirty_databases = _source.get_all_databases()

    _databases = []
    
    # Cleaning the database list
    for _database in _dirty_databases:
        
        ###
        # Specific rules for Muzzley Database
        #
        
        if _database == 'muzzley_migrations':            
            continue

        if _database.startswith('muzzley_'):
            _databases.append(_database)
        
        #
        # End Specific rules
        ###

    _start_time = time.time()

    _max_workers = args.max_workers

    for _database in _databases:
        
        print('\n\nEexport and importing: {}: '.format(_database))
                
        await _target.import_database(_database, _source, _max_workers)
        await _target.import_database_indexes(_database, _source, _max_workers)


    print('--- %s seconds ---' % (time.time() - _start_time))


if __name__ == '__main__':

    _parser = argparse.ArgumentParser(description='Export CouchDB to MongoDB Script')
    _parser.add_argument('--couchdb-source-host', type=str, required=True, metavar='127.0.0.1', help='CouchDB Host')
    _parser.add_argument('--couchdb-source-port', type=int, required=True, metavar=5984, help='CouchDB Port')
    _parser.add_argument('--mongodb-target-host', type=str, required=True, metavar='127.0.0.1', help='CouchDB Host')
    _parser.add_argument('--mongodb-target-port', type=int, required=True, metavar=27017, help='CouchDB Port')
    _parser.add_argument('--databases', type=str, required=True, metavar='a,b,c OR all', help='CouchDB databases to be exported')
    _parser.add_argument('--max-workers', type=int, required=False, metavar=5, default=multiprocessing.cpu_count()>>1 or 1, help='Max concurrent workers migrating structure, data, and indexes')
    _parser.add_argument('--source-directory', type=str, required=False, metavar='/home/example/dump_files/', default=None, help='Directory that contains all .json files extracted from CouchDB with: curl -X GET \'http://<host>:<post>/<database>/_all_docs?include_docs=true\' > <database>.json')
    
    _args = _parser.parse_args()

    _loop = asyncio.get_event_loop()
    _loop.run_until_complete(main(_args))
