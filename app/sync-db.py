#!/usr/local/bin/python

import requests
from bson import ObjectId
from pymongo import MongoClient
import datetime
import os
import time
import logging

## SET THESE 
SYNC_DESTINATION = ''
logging.basicConfig(level=logging.INFO)


MONGO_HOST = os.environ.get('MONGO_HOST', '127.0.0.1')
MONGO_URI = "mongodb://{}:27017/".format(MONGO_HOST)
MONGO_COLLECTION = 'marketcity'

SLEEP = 60 # seconds

mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_COLLECTION]


if __name__ == "__main__":

    if not SYNC_DESTINATION:
        'Not syncing requests from this server'

    # for each row in requests collection
    # where objectId is less than current run time
    # preform request to web server
    # if successful remove row from db

    success = 0
    fail = 0

    logging.warn('SYNC Starting Sync DB script')
    logging.warn('SYNC Getting requests from %s', MONGO_URI)

    while True:
        query = {'_id': {'$lt': ObjectId.from_datetime(datetime.datetime.utcnow())}}

        for req in db.sync.find(query):

            status_ok = True

            method = req.get('method','').lower()
            url = req.get('url')
            data = req.get('data', {})

            if method and url:
                url = SYNC_DESTINATION + url
                r = requests.request(method, url, data=data)
                status_ok = r.status_code == 200

            if not status_ok:
                fail += 1
                print('Failed sync', method, url, data, sep='\t')
            else:
                success += 1
                print('Success sync', method, url, data, sep='\t')
                db.sync.delete_one({'_id':req['_id']})

        logging.info('SYNC Completed with %s successful and %s failed requests', success, fail)
        time.sleep(60)
