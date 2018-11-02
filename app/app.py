from flask import Flask, jsonify, request, render_template
from flask_pymongo import PyMongo
from bson import ObjectId
import pymongo
import datetime
import os

app = Flask(__name__)

mongo_host = os.environ.get('MONGO_HOST', '127.0.0.1')

app.config["MONGO_URI"] = "mongodb://{}:27017/marketcity".format(mongo_host)
mongo = PyMongo(app)


player_schema = ['email','firstName','lastName','displayName','phone','postcode']
player_presenter = ['email','firstName','lastName','displayName','phone','postcode','updatedAt']

score_schema = ['email','displayName','score']
score_presenter = ['email','displayName','score']


@app.route("/")
def hello():
    return "Welcome to web server of StartVR for Market City"


@app.route('/scores', methods=['POST', 'GET'])
def scores():

    # POST
    if request.method == 'POST':
        #result = mongo.db.scores.delete_many({})

        if request.is_json:
            content = request.get_json()
        else:
            content = request.form

        if not content:
            return 'Bad request: Please send JSON or from data containing {}'.format(score_schema), 400

        doc = dict()
        for param in score_schema:
            if param not in content or not content[param]:
                return 'Bad request: Missing {}'.format(param), 400     
            doc[param] = content[param]

        mongo.db.scores.save(doc)
        return 'Ok', 200

    # GET
    now = datetime.datetime.utcnow()
    query = {
        '_id': {
            '$gte': ObjectId.from_datetime(now - datetime.timedelta(days=1)),
            '$lt': ObjectId.from_datetime(now)
        },
    }
    sort = 'score'
    skip = request.args.get('skip', 0)
    limit = request.args.get('limit', 0)

    scores = []
    for score in mongo.db.scores.find(query).sort(sort, pymongo.DESCENDING).skip(skip).limit(limit): 
        scores.append({
            'time': score['_id'].generation_time.isoformat(),
            'score': score.get('score', 0),
            'displayName': score.get('displayName' ,''),
            'email': score.get('email',''),
        })
    return jsonify({
        'scores': scores
    })


@app.route('/players', methods=['GET'])
def players():
    
    # GET
    now = datetime.datetime.utcnow()
    query = {
        'updatedAt': {
            '$gte': now - datetime.timedelta(days=1),
            '$lt': now
        },
    }
    sort = 'updatedAt'
    skip = request.args.get('skip', 0)
    limit = request.args.get('limit', 0)

    players = []
    for player in mongo.db.players.find(query).sort(sort, pymongo.DESCENDING).skip(skip).limit(limit): 
        players.append({
            param: player.get(param) 
            for param in player_presenter
        })
    return jsonify({
        'players': players
    })


@app.route('/signup', methods=['GET','POST'])
def signup():
    # POST
    if request.method == 'POST':
        if request.is_json:
            content = request.get_json()
        else:
            content = request.form

        if not content:
            return 'Bad request: Please send JSON or from data containing {}'.format(player_schema), 400

        doc = dict()
        for param in player_schema:
            if param not in content or not content[param]:
                return 'Bad request: Missing {}'.format(param), 400     
            doc[param] = content[param]

        # use email as player primary key
        doc['_id'] = content['email']
        doc['updatedAt'] = datetime.datetime.utcnow()
        mongo.db.players.save(doc)
        return render_template('signup.html', firstName=content['firstName'], lastName=content['lastName'])

    return render_template('signup.html')


def ignore_exception(IgnoreException=Exception,DefaultVal=None):
    """ Decorator for ignoring exception from a function
    e.g.   @ignore_exception(DivideByZero)
    e.g.2. ignore_exception(DivideByZero)(Divide)(2/0)
    """
    def dec(function):
        def _dec(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except IgnoreException:
                return DefaultVal
        return _dec
    return dec


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=8080)