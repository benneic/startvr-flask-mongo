#!/usr/local/bin/python

import requests
from bson import ObjectId
from pymongo import MongoClient
import datetime
import os
import time
import logging

## SET THESE 
SYNC_DESTINATION = '' # should be 'http://server:port'
logging.basicConfig(level=logging.DEBUG)


MONGO_HOST = os.environ.get('MONGO_HOST', '127.0.0.1')
MONGO_URI = "mongodb://{}:27017/".format(MONGO_HOST)
MONGO_COLLECTION = 'marketcity'

SLEEP = 60 # seconds

mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_COLLECTION]


if __name__ == "__main__":

    if not SYNC_DESTINATION:
        logging.error('[SYNC-DB] Not syncing requests from this server')
        exit()

    if SYNC_DESTINATION[-1] == '/':
        # remove trailing slash
        SYNC_DESTINATION = SYNC_DESTINATION[:-1]

    # for each row in requests collection
    # where objectId is less than current run time
    # preform request to web server
    # if successful remove row from db

    logging.warn('[SYNC-DB] Starting Sync DB script')
    logging.warn('[SYNC-DB] Getting requests from %s', MONGO_URI)

    while True:
        query = {'_id': {'$lt': ObjectId.from_datetime(datetime.datetime.utcnow())}}
        success = 0
        fail = 0
        for req in db.sync.find(query):

            status_ok = True

            method = req.get('method','').lower()
            url = req.get('url')
            data = req.get('data', {})

            if method and url:
                url = SYNC_DESTINATION + url
                r = requests.request(method, url, data=data)

            logging.debug('[SYNC-DB] %s %s returned %s %s', method, url, r.status_code, data)

            if r.status_code != 200:
                fail += 1
            else:
                success += 1
                db.sync.delete_one({'_id':req['_id']})

        logging.log(
            logging.INFO if success or fail else logging.DEBUG,
            '[SYNC-DB] Completed with %s successful and %s failed requests', 
            success, 
            fail
        )

        time.sleep(60)
