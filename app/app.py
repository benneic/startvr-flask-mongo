from flask import Flask, jsonify, request, render_template, Response
from flask_pymongo import PyMongo
from bson import ObjectId
import pymongo
import datetime
import os

app = Flask(__name__)

mongo_host = os.environ.get('MONGO_HOST', '127.0.0.1')
app.config["MONGO_URI"] = "mongodb://{}:27017/marketcity".format(mongo_host)

mongo = PyMongo(app)

player_schema = ['email','firstName','lastName','displayName','phone','postcode','hand']
player_presenter = ['email','firstName','lastName','displayName','phone','postcode','updatedAt','hand']

score_schema = ['email','displayName','score','easteregg']
score_presenter = ['email','displayName','score','easteregg']

iso8601_format_string = '%Y-%m-%dT%H:%M:%SZ'


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

    end = request.args.get('to')
    if end:
        try:
            end = datetime.datetime.strptime(end, iso8601_format_string)
        except ValueError:
            return 'Bad request: Param "to" format required in UTC time zone and ISO8601 format {}'.format(iso8601_format_string), 400   
    else:
        end = datetime.datetime.utcnow()

    start = request.args.get('from')
    if start:
        try:
            start = datetime.datetime.strptime(start, iso8601_format_string)
        except ValueError:
            return 'Bad request: Param "to" format required in UTC time zone and ISO8601 format {}'.format(iso8601_format_string), 400   
    else:
        start = end - datetime.timedelta(days=1)

    query = {
        '_id': {
            '$gte': ObjectId.from_datetime(start),
            '$lt': ObjectId.from_datetime(end)
        },
    }
    sort = 'score'
    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', 0))
    output = request.args.get('output')

    
    cursor = mongo.db.scores.find(query).sort(sort, pymongo.DESCENDING).skip(skip).limit(limit)


    if output == 'json':
        scores = []
        for score in cursor: 
            scores.append({
                'time': score['_id'].generation_time.isoformat(),
                'score': score.get('score', 0),
                'easteregg': score.get('easteregg', False),
                'email': score.get('email',''),
                'displayName': score.get('displayName' ,''),
            })
        
        return jsonify({
            'scores': scores,
            'query': {
                'from': start.isoformat(),
                'to': end.isoformat(),
                'sort': sort,
                'skip': skip,
                'limit': limit
            }
        })

    # output in delimited format
    headers = {}
    if output == 'csv':
        filename = "VR Players {} to {}".format(start.isoformat()[:10], end.isoformat()[:10])
        headers['Content-Disposition'] = "attachment; filename='{}.csv'".format(filename)
        mimetype = 'text/csv; charset=utf-8'
        seperator = ','
    else:
        mimetype = 'text/text; charset=utf-8'
        seperator = '|'

    def generate():
        for score in cursor: 
            yield "{1}{0}{2}{0}{3}{0}{4}{0}{5}\n".format(
                seperator,
                score['_id'].generation_time.isoformat(),
                score.get('score', 0),
                score.get('easteregg', False),
                score.get('email',''),
                score.get('displayName' ,'')
            )
    
    return Response(generate(), headers=headers, mimetype=mimetype)


@app.route('/players', methods=['GET'])
def players():
    
    # GET
    end = request.args.get('to')
    if end:
        try:
            end = datetime.datetime.strptime(end, iso8601_format_string)
        except ValueError:
            return 'Bad request: Param "to" format required in UTC time zone and ISO8601 format {}'.format(iso8601_format_string), 400   
    else:
        end = datetime.datetime.utcnow()

    start = request.args.get('from')
    if start:
        try:
            start = datetime.datetime.strptime(start, iso8601_format_string)
        except ValueError:
            return 'Bad request: Param "to" format required in UTC time zone and ISO8601 format {}'.format(iso8601_format_string), 400   
    else:
        start = end - datetime.timedelta(days=1)

    query = {
        'updatedAt': {
            '$gte': start,
            '$lt': end
        },
    }
    sort = 'updatedAt'
    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', 0))
    output = request.args.get('output')

    cursor = mongo.db.players.find(query).sort(sort, pymongo.DESCENDING).skip(skip).limit(limit)

    if output == 'json':
        players = []
        for player in cursor: 
            players.append({
                param: player.get(param) 
                for param in player_presenter
            })
        return jsonify({
            'players': players,
            'query': {
                'from': start.isoformat(),
                'to': end.isoformat(),
                'sort': sort,
                'skip': skip,
                'limit': limit
            }
        })
    
    # output in delimited format
    headers = {}
    if output == 'csv':
        filename = "VR Scores {} to {}".format(start.isoformat()[:10], end.isoformat()[:10])
        headers['Content-Disposition'] = "attachment; filename='{}.csv'".format(filename)
        mimetype = 'text/csv; charset=utf-8'
        seperator = ','
    else:
        mimetype = 'text/text; charset=utf-8'
        seperator = '|'

    def generate():
        for player in cursor: 
            yield '{1}{0}"{2}"{0}"{3}"{0}"{4}"{0}{5}{0}"{6}"{0}"{7}"{0}"{8}"\n'.format(
                seperator,
                player.get('updatedAt').isoformat(),
                player.get('hand', 'both'),
                player.get('email',''),
                player.get('phone',''),
                player.get('postcode',''),
                player.get('displayName' ,''),
                player.get('firstName' ,''),
                player.get('lastName' ,'')
            )
    
    return Response(generate(), headers=headers, mimetype=mimetype)


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


@app.route('/', methods=['GET'])
def report():
    return render_template('index.html')


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
    app.run(host='0.0.0.0', debug=True, port=5000)