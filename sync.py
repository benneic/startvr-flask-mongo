import requests
from bson import ObjectId
from pymongo import MongoClient
import datetime
import os

MONGO_HOST = os.environ.get('MONGO_HOST', '127.0.0.1')
MONGO_URI = "mongodb://{}:27017/".format(MONGO_HOST)
MONGO_COLLECTION = 'marketcity'

mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_COLLECTION]

if __name__ == "__main__":
    # for each row in requests collection 
    # preform request to web server
    # if successful remove row from db
    print('not implemented yet')