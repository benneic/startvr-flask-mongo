from flask import Flask, jsonify, request, render_template
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/marketcity"

mongo = PyMongo(app)

@app.route("/")
def hello():
    return "Welcome to web server of StartVR for Market City"


@app.route('/scores', methods=['POST', 'GET'])
def scores():
    # POST
    if request.method == 'POST':
        
        #result = mongo.db.scores.delete_many({})
        if not request.is_json:
            return 'Bad request: Please send JSON containing email, score and displayName', 400
        content = request.get_json()
        if 'email' not in content: 
            return 'Bad request: Missing email', 400 
        if 'score' not in content: 
            return 'Bad request: Missing score (must be integer)', 400 
        if 'displayName' not in content: 
            return 'Bad request: Missing displayName', 400 
        doc = {
            'email': content['email'],
            'score': content['score'],
            'displayName': content['displayName'],
        }        
        mongo.db.scores.save(doc)
        return 'Ok', 200

    # GET
    fromDate = request.args.get('from', '')
    query = {
        '_id' : {'$gte': fromDate} 
    }
    scores = []
    for score in mongo.db.scores.find({}): 
        scores.append({
            'time': score['_id'].generation_time.isoformat(),
            'score': score.get('score', 0),
            'displayName': score.get('displayName' ,''),
            'email': score.get('email',''),
        })
    return jsonify({
        'scores': scores
    })


@app.route('/players', methods=['GET','POST'])
def players():
    # POST
    if request.method == 'POST':
        if request.is_json:
            content = request.get_json()
        else:
            content = request.form
        doc = dict()
        for param in ['email','firstName','lastName','displayName','phone']:
            if param not in content: 
                return 'Bad request: Missing {}'.format(param), 400 
            doc[param] = content[param]
        # use email as player primary key
        doc['_id'] = content['email']
        mongo.db.players.save(doc)
        return 'OK', 200
    
    # GET
    players = []
    for player in mongo.db.players.find({}): 
        players.append({
            'displayName': player.get('displayName' ,''),
            'email': player.get('email',''),
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
        doc = dict()
        for param in ['email','firstName','lastName','displayName','phone','postcode']:
            if param not in content or not content[param]:
                return 'Bad request: Missing {}'.format(param), 400 
            doc[param] = content[param]
        # use email as player primary key
        doc['_id'] = content['email']
        mongo.db.players.save(doc)
        return render_template('signup.html', firstName=content['firstName'], lastName=content['lastName'])
    
    # GET
    players = []
    for player in mongo.db.players.find({}): 
        players.append({
            'displayName': player.get('displayName' ,''),
            'email': player.get('email',''),
        })
    
    return render_template('signup.html')


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=8080)