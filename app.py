import os
import traceback
from dateutil import parser
from io import BytesIO
import pandas as pd
import urllib.parse
import nanoid
import copy
import time
import json
import hashlib
import datetime
from PIL import Image
from flask_mysqldb import MySQL
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, make_response

app = Flask(__name__)

app.config["MYSQL_USER"] = os.environ.get('MYSQL_USER')
app.config["MYSQL_HOST"] = os.environ.get('MYSQL_SERVER')
app.config["MYSQL_PASSWORD"] = os.environ.get('MYSQL_PW')
app.config["MYSQL_DB"] = os.environ.get('MYSQL_DB')
app.config["MYSQL_CURSORCLASS"] = "DictCursor"


app.config['UPLOAD_FOLDER'] = 'logos'

mysql = MySQL(app)


NAV = {'top': [
            {'url': '/', 'label': 'Home'},
            {'url': '/create', 'label': 'New Challenge'},
            {'url': '/privacy', 'label': 'Privacy Note'},
        ]}


def result_query(meta):
    cur = mysql.connection.cursor()
    # unfortunately the start-date is stored as 00:00:00 UTC and the day is already "on" for 12h in some parts of the world, so we need to extend the range by that much
    result_query = 'SELECT SUM('+meta['challenge_type_metric']+') as result, MAX(data_synced) as synced, device_id, data_username FROM user_data WHERE (data_timestamp >= %s-12*60*60 OR data_timestamp=0) AND challenge_id=%s GROUP BY data_username, device_id ORDER BY result DESC'
    cur.execute(result_query, (meta['challenge_start_timestamp'], meta['challenge_id'],))
    return cur.fetchall()


@app.route("/data", methods=['GET', 'POST'])
def result():
    data = request.get_json()

    if "c" not in data.keys():
        return jsonify({"status": "please join\na challenge first"})

    challenges = []
    your_rank = 0
    diff_steps = ''

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM challenges c, challenge_types t WHERE challenge_identifier=%s AND c.challenge_type=t.challenge_type_id", (data['c'],))
    challenges = cur.fetchall()
    
    if type(challenges) is not tuple or len(challenges) != 1:
        return jsonify({"status": "please join\na new challenge first"})

    meta = challenges[0]
    diff_steps = 'You are alone! Share\n'+meta['challenge_identifier']+'\nto invite others!'
    challenge_id = meta['challenge_id']
    if meta['challenge_start_timestamp'] > datetime.datetime.now().timestamp():
        return jsonify({"status": "this challenge has\nnot yet started!"})
    if meta['challenge_end_timestamp'] < datetime.datetime.now().timestamp():
        return jsonify({"status": "this challenge has ended!"})
    i = 0
    user_data = json.loads(data['d'])
    tz_offset = 0
    try:
        tz_offset = int(data['o'])
    except:
        pass
    if len(user_data) % 7 != 0:
        return jsonify({"status": "please update app", 'c': meta['challenge_name']})
    while i < len(user_data):
        if int(user_data[i]) < meta['challenge_start_timestamp'] and int(user_data[i]) != 0:
            # we can still store the data, even though it is not within the timeframe of the challenge
            pass
        cur.execute("SELECT COUNT(*) as is_in FROM user_data WHERE data_timestamp=%s AND challenge_id=%s AND data_username=%s AND device_id=%s", (user_data[i], challenge_id, data['u'], data['i']))
        if cur.fetchone()['is_in'] == 0:
            cur.execute("INSERT INTO user_data (device_id, data_timestamp, data_steps, data_calories, data_active_calories, data_active_minutes, data_floors_climbed, data_distance, data_synced, data_username, data_team_name, data_timezone_offset, challenge_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (data['i'], user_data[i], user_data[i+1], user_data[i+2], user_data[i+3], user_data[i+4], user_data[i+5], user_data[i+6], datetime.datetime.now().timestamp(), data['u'], data['t'], tz_offset, challenge_id))
            mysql.connection.commit()
        else:
            cur.execute("UPDATE user_data SET data_steps=%s, data_calories=%s, data_active_calories=%s, data_distance=%s, data_active_minutes=%s, data_floors_climbed=%s, data_synced=%s, data_timezone_offset=%s WHERE data_username=%s AND challenge_id=%s AND data_timestamp=%s and device_id=%s", (user_data[i+1], user_data[i+2], user_data[i+3], user_data[i+4], user_data[i+5], user_data[i+6], datetime.datetime.now().timestamp(), tz_offset, data['u'], challenge_id, user_data[i], data['i']))
        i = i + 7
        
    mysql.connection.commit()

    ranking = result_query(meta)
    for i, rank in enumerate(ranking):
        if rank['device_id'] == data['i']:
            if len(ranking) > 1:
                if i == 0:
                    diff_steps = str(rank['result'] - ranking[i+1]['result']) + ' ahead of\n🎉'+str(ranking[i+1]['data_username'])+'!'
                else:
                    diff_steps = str(ranking[i-1]['result'] - rank['result']) + ' behind\n🏃'+str(ranking[i-1]['data_username'])+'!'
            your_rank = str(i + 1)
            break
    
    reply = {'status': str(your_rank) + '/' + str(len(ranking)) + ' ' +str(diff_steps), 'c': meta['challenge_name'] + '\n' + data['u']}
    #emoji_string = '🚀⭐😀🥳💩🤡🎃🥵\n🌤💪🎅☔☀️🌤️🌦️⛈️🌨️❄️\n🚴🏊🏃🧘🥇🥈🥉'
    # Working on Fenix5s&Vivoactive3 headline
    #emoji_string = '😀😃😄😁😆\n😅😂☺️😊😇🙂\n🙃😉😌😍😘😗😙\n😚😋😛😝😜🤓😎'
    #emoji_string += '🚲🚴🏊🏃💩😱😭\n🏅👏👍👎🙏🍺🎊🎉\n🔥❤️💔💯❤️‍🔥💖♥️\n'
    #reply = {'status': 'Emoji-Test', 'c': emoji_string}
    return jsonify(reply)


@app.route("/leaderboard", methods=['GET', 'POST'])
def leaderboard():
    if request.method == 'GET' and 'key' in request.values.keys() and len(request.values['key']) > 0:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM challenges c, challenge_types t WHERE challenge_api_key=%s AND c.challenge_type=t.challenge_type_id", (request.values['key'],))
        meta = cur.fetchone()
        if meta is not None:
            nav = copy.deepcopy(NAV)
            total = 0
            data = result_query(meta)
            for i, row in enumerate(data):
                data[i]['synced'] = datetime.datetime.utcfromtimestamp(row['synced']).strftime('%Y-%m-%d %H:%M')
                try:
                    total += row['result']
                except:
                    pass
            context = {'data': data, 'challenge_type_text': meta['challenge_type_text'], 'challenge_name': meta['challenge_name'], 'challenge_short': meta['challenge_identifier'], 'nav': nav,}
            cur.execute("SELECT image_key_hash as image_key FROM image_keys WHERE active=1")
            context['image_key'] = cur.fetchone()['image_key']
            context['total'] = total
            context['challenge_start'] = datetime.datetime.utcfromtimestamp(meta['challenge_start_timestamp']).strftime('%Y-%m-%d')
            context['challenge_end'] = datetime.datetime.utcfromtimestamp(meta['challenge_end_timestamp']).strftime('%Y-%m-%d')
            return render_template('leaderboard.html', **context)
    return redirect('/')


@app.route("/logo", methods=['GET', 'POST'])
def logo():
    logo = 'logo.png'
    if 'k' in request.values.keys() and 'c' in request.values.keys():
        cur = mysql.connection.cursor()
        cur.execute("SELECT c.challenge_identifier as challenge_identifier FROM challenges c, image_keys k WHERE c.challenge_identifier=%s AND k.image_key_hash=%s and k.active=1", (request.values['c'], request.values['k'],))
        challenges = cur.fetchall()
        if type(challenges) is tuple and len(challenges) == 1:
            logo = challenges[0]['challenge_identifier'] + '.png'
    return send_from_directory('logos', logo)


@app.route("/", methods=["GET"])
def index():
    nav = copy.deepcopy(NAV)
    nav['top'][0]['is_active'] = True
    context = {'nav': nav,}
    return render_template('index.html', **context)


def hash_string(text):
    text = text + '283djkfnsHG623löM78NB'
    return hashlib.sha512(text.encode()).hexdigest()[:64]


@app.route("/create", methods=["GET", "POST"])
def create():
    time.sleep(2)
    nav = copy.deepcopy(NAV)
    nav['top'][1]['is_active'] = True
    context = {'nav': nav, 'error': ''}
    if request.method == 'POST':
        timestamp_start = 0
        timestamp_end = 0
        challenge_type = 0
        challenge_name = ''
        if 'challenge_name' not in request.values.keys() or len(request.values['challenge_name'].strip()) < 5 or len(request.values['challenge_name'].strip()) > 20:
            context['error'] = 'Challenge Name must have a length between 5 and 20 chars.<br />'
        #challenge_name = urllib.parse.quote(request.values['challenge_name'].strip())
        challenge_name = request.values['challenge_name'].strip()
        try:
            print(request.values['start_date'])
            print(request.values['end_date'])
            timestamp_start = parser.isoparse(request.values['start_date'] + ' 00:00Z').timestamp()
        except:
            # failed to parse 
            context['error'] += 'Can\'t parse start date<br />'
        try:
            timestamp_end = parser.isoparse(request.values['end_date'] + ' 00:00Z').timestamp()
        except:
            # failed to parse 
            context['error'] += 'Can\'t parse end date<br />'
        if timestamp_end <= timestamp_start:
            context['error'] += 'End-date must be after start-date<br />'
        if timestamp_start <= datetime.datetime.now().timestamp() - 12*60*60:
            context['error'] += 'Start-date must be in the future<br />'
        if timestamp_end > datetime.datetime.now().timestamp() + 400*24*60*60:
            context['error'] += 'End-date must be within 400 days from now<br />'
        challenge_short = nanoid.generate(size=5)
        challenge_api_key = hash_string(challenge_short)
        challenge_admin_key = hash_string(challenge_short + 'gihjrw4eofn/(&%&dw)')
        challenge_image = request.files['challenge_logo']
        try:
            challenge_type = int(request.values['target_metric'])
        except:
            context['error'] += 'invalid target metric<br />'
        if challenge_type < 1 or challenge_type > 6:
            context['error'] += 'invalid target metric<br />'
        try:
            challenge_image = Image.open(request.files['challenge_logo'])
        except:
            context['error'] += 'Can\'t parse image<br />'
        if context['error'] == '':
            img_size = challenge_image.size
            # 490px is the highest resolution garmin at the moment - so half of that should be enough
            img_ratio = 250/img_size[0]
            challenge_image = challenge_image.resize((int(img_size[0]*img_ratio), int(img_size[1]*img_ratio)))
            path = os.path.join(app.config['UPLOAD_FOLDER'], challenge_short + '.png')
            challenge_image.save(path)
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO `challenges` (`challenge_id`, `challenge_name`, `challenge_start_timestamp`, `challenge_end_timestamp`, `challenge_tz`, `challenge_identifier`, `challenge_color`, `challenge_teams`, `challenge_api_key`, `challenge_admin_key`, `challenge_type`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                        (
                            challenge_name,
                            timestamp_start,
                            timestamp_end,
                            None,
                            challenge_short,
                            '00AA00',
                            0,
                            challenge_api_key,
                            challenge_admin_key,
                            challenge_type
                        ))
            mysql.connection.commit()
            return redirect(url_for('admin', admin_key=challenge_admin_key))
    cur = mysql.connection.cursor()
    cur.execute("SELECT challenge_type_id, challenge_type_text FROM challenge_types ORDER BY challenge_type_id")
    context['challenge_types'] = cur.fetchall()
    return render_template('create.html', **context)


@app.route("/admin", methods=["GET"])
def admin():
    nav = copy.deepcopy(NAV)
    context = {'nav': nav, 'error': ''}
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM challenges WHERE challenge_admin_key=%s", (request.values['admin_key'],))
    data = cur.fetchone()
    if data is None:
        time.sleep(2)
        return redirect('/')
    cur.execute("SELECT image_key_hash as image_key FROM image_keys WHERE active=1")
    context['image_key'] = cur.fetchone()['image_key']
    cur.execute("SELECT challenge_type_text FROM challenge_types WHERE challenge_type_id=%s", (data['challenge_type'],))
    context['challenge_type_text'] = cur.fetchone()['challenge_type_text']
    context['challenge_identifier'] = data['challenge_identifier']
    context['challenge_name'] = data['challenge_name']
    context['api_key'] = data['challenge_api_key']
    context['admin_key'] = data['challenge_admin_key']
    context['start_date'] = datetime.datetime.fromtimestamp(data['challenge_start_timestamp']).strftime('%Y-%m-%d')
    context['end_date'] = datetime.datetime.fromtimestamp(data['challenge_end_timestamp']).strftime('%Y-%m-%d')
    return render_template('admin.html', **context)


@app.route("/excel", methods=["GET", "POST"])
def excel():
    result = {}
    if request.method == 'GET' and 'key' in request.values.keys() and len(request.values['key']) > 0:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM challenges c, challenge_types t WHERE challenge_api_key=%s AND c.challenge_type=t.challenge_type_id", (request.values['key'],))
        meta = cur.fetchone()
        if meta is None:
            print("No challenge found")
            return jsonify(result)
        output = BytesIO()
        writer = pd.ExcelWriter(output)
        data = result_query(meta)
        for i, row in enumerate(data):
            del data[i]['device_id']
            data[i]['synced'] = datetime.datetime.utcfromtimestamp(row['synced']).strftime('%Y-%m-%d %H:%M')
        pd.DataFrame(data).to_excel(writer, index=False)
        writer.close()
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename="+meta['challenge_name']+ "_" + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M') + ".xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    print("No key found")
    return jsonify(result)


@app.route("/delete", methods=["GET", "POST"])
def delete():
    time.sleep(2)
    if request.method == 'GET' and 'k' in request.values.keys() and len(request.values['k']) > 0:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM challenges WHERE challenge_admin_key=%s", (request.values['k'],))
        meta = cur.fetchone()
        if meta is not None:
            cur.execute("DELETE FROM user_data WHERE challenge_id=%s", (meta['challenge_id'],))
            cur.execute("DELETE FROM challenges WHERE challenge_id=%s", (meta['challenge_id'],))
            mysql.connection.commit()
            try:
                os.unlink('logos/' + meta['challenge_identifier'] + '.png')
            except:
                pass
    return redirect('/')


@app.route("/api", methods=["GET", "POST"])
def api():
    result = {}
    if 'key' in request.values.keys() and len(request.values['key']) > 0:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM challenges c, challenge_types t WHERE c.challenge_api_key=%s AND c.challenge_type=t.challenge_type_id", (request.values['key'],))
        meta = cur.fetchone()
        cur.execute("SELECT MAX(data_synced) as updated FROM user_data ud WHERE challenge_id = %s", (meta['challenge_id'],))
        updated = cur.fetchone()['updated']
        # TODO: does any of the target-modes require some calculations?
        return jsonify({'data': result_query(meta), 'type_id': meta['challenge_type_id'], 'type': meta['challenge_type_text'], 'updated': updated, 'start_date': meta['challenge_start_timestamp'], 'end_date': meta['challenge_end_timestamp']})
    return jsonify(result)


@app.route("/privacy", methods=["GET"])
def privacy():
    nav = copy.deepcopy(NAV)
    nav['top'][2]['is_active'] = True
    context = {'nav': nav,}
    return render_template('privacy.html', **context)


if __name__ == "__main__":
    app.run(debug=True)
