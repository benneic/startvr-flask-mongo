from flask import Flask, jsonify, request, render_template, Response, redirect, url_for
from flask.json import JSONEncoder
from flask_pymongo import PyMongo
from flask_moment import Moment
from bson import ObjectId
import pymongo
import datetime
import os


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder

mongo_host = os.environ.get('MONGO_HOST', '127.0.0.1')
app.config["MONGO_URI"] = "mongodb://{}:27017/marketcity".format(mongo_host)

mongo = PyMongo(app)

moment = Moment(app)

station_schema = ['status']
# Players that sign up to play via the /signup endpoint look like this in the database
# they are uniquely identified by email field on the _id key
# waiting field is to signify that a play has signed up (either once or again) and is waiting to play
player_schema = ['email','firstName','lastName','displayName','phone','postcode','hand']
player_schema_hidden = ['waiting', 'started', 'updatedAt']
player_presenter = ['email','firstName','lastName','displayName','phone','postcode','updatedAt','hand','scores']

# Scores are populated by the game using the email field of each player
# there can be many scores per player
# they are uniquely identified by _id ObjectId default key which is also the timestamp of the score
score_schema = ['email','displayName','score','easteregg']
score_presenter = ['email','displayName','score','easteregg']

# Each station would like to know which player is next, so we have a next player collection for that
# there can only be one next player per station and a player can only play one game at a time
# each station is uniquely identified by an integer and is stored in _id key
next_player_schema = ['email','displayName']
next_player_schema_hidden = ['isReady']

ISO8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

def parse_isodate(date_string):
    return datetime.datetime.strptime(date_string, ISO8601_FORMAT)

@app.route('/station/<station>', methods=['POST'])
def station(station):
    if not station:
        return '', 404

    content = request.form
    if not content:
        return 'Bad request: Please send JSON or from data containing {}'.format(next_player_schema), 400

    doc = {
        '_id': station
    }
    for param in station_schema:
        if param not in content or content[param] == '':
            return 'Bad request: Missing {}'.format(param), 400     
        doc[param] = content[param]

    mongo.db.station.save(doc)
    return '', 204


@app.route('/station/<station>/status')
def station_status(station):
    if not station:
        return '', 404
    result = mongo.db.station.find_one({'_id': station})
    if not result:
        return '', 404
    return result.get('status', 'Waiting for status'), 200
    

@app.route('/station/<station>/player', methods=['GET', 'POST'])
def get_next_player(station):
    # either returns 200 with a result, 204 when successful but no result, or 404 when station not found

    # station has started playing with the next player
    if request.method == 'POST':
        # mongo.db.next_player.delete_one({'_id':station})
        # successfully processed reponse but not return any content
        return '', 204

    next_player = mongo.db.next_player.find_one({'_id':station})
    if next_player:
        mongo.db.next_player.update_one({'_id':station}, {'$set':{'isReady':True}})
        player = mongo.db.players.find_one({'_id': next_player.get('email')})
        return "{0}|{1}|{2}|{3}\n".format(
                player.get('email'),
                player.get('displayName' ,''),
                player.get('hand', 'right'),
                player.get('started', False)
            )

    # successfully received reponse but not returning any content
    # because there is no player waiting yet
    return '', 204

@app.route('/reset/<station>', methods=['GET'])
def manage_reset(station):
    # get the next player for this station
    next_player = mongo.db.next_player.find_one({'_id':station})
    if next_player:
        mongo.db.next_player.delete_one({'_id':station})
    
    return 'OK', 200
            
@app.route('/next/<station>', methods=['POST', 'GET'])
def manage_next_player(station):
    # GET    - return all players waiting to play and the current player waiting to play next for this station
    # POST   - assign a player to a station to play next

    if request.method == 'POST':
        content = request.form
        if not content:
            return 'Bad request: Please send JSON or from data containing {}'.format(next_player_schema), 400

        # if player sent is already in next queue then remove them and make them wait again
        # otherwise add this player to the wait queue
        doc = {
            '_id': station,
            'isReady': False
        }
        for param in next_player_schema:
            if param not in content or content[param] == '':
                return 'Bad request: Missing {}'.format(param), 400     
            doc[param] = content[param]
            
        # get the next player for this station
        next_player = mongo.db.next_player.find_one({'_id':station})

        if not next_player:
            mongo.db.next_player.save(doc)
            mongo.db.players.update_one({'_id': doc['email']}, {'$unset':{'waiting': ''}})
            mongo.db.players.update_one({'_id': doc['email']}, {'$unset':{'started': ''}})
        
        elif next_player['email'] == content['email'] and content['action'] == 'start':
            mongo.db.players.update_one({'_id': next_player['email']}, {'$unset':{'waiting': ''}})
            mongo.db.players.update_one({'_id': next_player['email']}, {'$set':{'started': True}})
            
        elif next_player['email'] == content['email'] and content['action'] == 'cancel':
            mongo.db.next_player.delete_one({'_id':station})
            mongo.db.players.update_one({'_id': next_player['email']}, {'$set':{'waiting': True}})
            mongo.db.players.update_one({'_id': next_player['email']}, {'$unset':{'started': ''}})

        elif next_player['email'] == content['email'] and content['action'] == 'complete':
            mongo.db.next_player.delete_one({'_id':station})
            mongo.db.players.update_one({'_id': next_player['email']}, {'$set':{'waiting': ''}})
            mongo.db.players.update_one({'_id': next_player['email']}, {'$unset':{'started': True}})            
            
        # else already a player waiting so dont do anything

        return redirect('/next/{}'.format(station))

    # get the next player for this station
    next_player = mongo.db.next_player.find_one({'_id':station})
    if next_player:
        is_ready = next_player.get('isReady', False)
        # get full player details
        next_player = mongo.db.players.find_one({'_id': next_player['email']})
        if next_player:
            next_player['isReady'] = is_ready

    #####
    # GET
    end = request.args.get('to')
    if end:
        try:
            end = parse_isodate(end)
        except ValueError:
            return 'Bad request: Param "to" format required in UTC time zone and ISO8601 format {}'.format(ISO8601_FORMAT), 400   
    else:
        end = datetime.datetime.utcnow()

    start = request.args.get('from')
    if start:
        try:
            start = parse_isodate(start)
        except ValueError:
            return 'Bad request: Param "start" format required in UTC time zone and ISO8601 format {}'.format(ISO8601_FORMAT), 400   
    else:
        start = end - datetime.timedelta(days=1)

    query = {
        'updatedAt': {
            '$gte': start,
            '$lt': end
        },
        'waiting': True
    }
    players = mongo.db.players.find(query).sort('updatedAt', pymongo.DESCENDING)

    return render_template('station.html', station=station, next_player=next_player, players_waiting=players)


def parse_bool(val):
    if val.upper() == 'TRUE' or val == '1':
        return True
    return False


@app.route('/score/<station>', methods=['POST'])
def score(station):  
    if not request.form:
        return 'Bad request: Please send form url encoded data containing {}'.format(score_schema), 400

    for param in score_schema:
        if param not in request.form or request.form[param] == '':
            return 'Bad request: Missing {}'.format(param), 400     
        
    score = request.form.get('score', 0, int)
    easteregg = request.form.get('easteregg', False, parse_bool)

    mongo.db.scores.save({
        'email': request.form['email'],
        'displayName': request.form['displayName'],
        'score': score,
        'easteregg': easteregg
    })
    
    # save score to players record
    mongo.db.players.update({ 
            "_id": request.form['email'] 
        }, {
            "$push": { "scores" : score}
        })

    # sync scores with upstream server
    mongo.db.sync.save({
        'url': '/score/0',
        'method': 'post',
        'data': request.form
    })    

    return 'OK', 200


@app.route('/testscore')
def testscore():  
    
    testdata = { 'score' : '5', 'easteregg' : 'false', 'email' : 'esfefsefsef@gdrgdrgdr.com', 'displayName' : 'MillieTest' }
    #score = testdata.get('score', 0, int)
    #easteregg = testdata.get('easteregg', False, parse_bool)

   
    return 'OK', 200



@app.route('/scores')
def scores():
    # return a report of scores in various formats

    end = request.args.get('to')
    if end:
        try:
            end = parse_isodate(end)
        except ValueError:
            return 'Bad request: Param "to" format required in UTC time zone and ISO8601 format {}'.format(ISO8601_FORMAT), 400   
    else:
        end = datetime.datetime.utcnow()

    start = request.args.get('from')
    if start:
        try:
            start = parse_isodate(start)
        except ValueError:
            return 'Bad request: Param "start" format required in UTC time zone and ISO8601 format {}'.format(ISO8601_FORMAT), 400   
    else:
        start = end - datetime.timedelta(days=1)

    query = {
        '_id': {
            '$gte': ObjectId.from_datetime(start),
            '$lt': ObjectId.from_datetime(end)
        },
    }

    sort = request.args.get('sort', 'score')
    if sort == 'time':
        sort = '_id'

    skip = request.args.get('skip', 0, int)
    limit = request.args.get('limit', 0, int)
    output = request.args.get('output')
    
    cursor = mongo.db.scores.find(query).sort(sort, pymongo.DESCENDING).skip(skip).limit(limit)

    if output in ['json','html']:
        scores = []
        for score in cursor: 
            scores.append({
                'time': score['_id'].generation_time,
                'score': score.get('score', 0),
                'easteregg': score.get('easteregg', False),
                'email': score.get('email',''),
                'displayName': score.get('displayName' ,''),
            })

        if output == 'html':
            return render_template('report-scores.html', scores=scores)
        
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
        newline = '\n'
    else:
        mimetype = 'text/text; charset=utf-8'
        seperator = '|'
        newline = '~~'
    def generate():
        for score in cursor: 
            yield "{1}{0}{2}{0}{3}{0}{4}{0}{5}{6}".format(
                seperator,
                score['_id'].generation_time.isoformat(),
                score.get('score', 0),
                score.get('easteregg', False),
                score.get('email',''),
                score.get('displayName' ,''),
                newline
            )
    
    return Response(generate(), headers=headers, mimetype=mimetype)


@app.route('/players', methods=['GET'])
def players():
    
    # GET
    end = request.args.get('to')
    if end:
        try:
            end = parse_isodate(end)
        except ValueError:
            return 'Bad request: Param "to" format required in UTC time zone and ISO8601 format {}'.format(ISO8601_FORMAT), 400   
    else:
        end = datetime.datetime.utcnow()

    start = request.args.get('from')
    if start:
        try:
            start = parse_isodate(start)
        except ValueError:
            return 'Bad request: Param "start" format required in UTC time zone and ISO8601 format {}'.format(ISO8601_FORMAT), 400   
    else:
        start = end - datetime.timedelta(days=1)

    query = {
        'updatedAt': {
            '$gte': start,
            '$lt': end
        },
    }
    
    sort = request.args.get('sort', 'time')
    if sort == 'time':
        sort = 'updatedAt'
    elif sort == 'score':
        sort = 'scores'        

    skip = request.args.get('skip', default=0, type=int)
    limit = request.args.get('limit', default=0, type=int)
    output = request.args.get('output', 'pipe')

    cursor = mongo.db.players.find(query).sort(sort, pymongo.DESCENDING).skip(skip).limit(limit)

    if output == 'html':
        return render_template('report-players.html', players=cursor)

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
            yield '{1}{0}{2}{0}{3}{0}{4}{0}{5}{0}{6}{0}{7}{0}{8}"\n'.format(
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
            if param not in content or content[param] == '':
                return 'Bad request: Missing {}'.format(param), 400     
            doc[param] = content[param]

        # use email as player primary key
        doc['_id'] = content['email']
        doc['updatedAt'] = datetime.datetime.utcnow()
        # all players are waiting to play each time they sign up
        doc['waiting'] = True
        # add a base scores array with no scoress
        doc['scores'] = []

        mongo.db.players.save(doc)

        # sync player with upstream server
        mongo.db.sync.save({
            'url': url_for('signup'),
            'method': 'post',
            'data': content
        })   

        return render_template('signup.html', firstName=content['firstName'], lastName=content['lastName'])

    return render_template('signup.html')


@app.route('/WIxJPpENIKApy0RkFqINnIVllmIJT99FIMeg9NqeKgxcPCUa5uhSMkdEm6lE', methods=['GET'])
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
