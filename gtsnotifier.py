# A script to notify the user when their deposited pokemon
# has been successfully traded on the pokemon x and y gts

import requests
import ConfigParser
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText

# Construct the config filename from the working directory of the script
configPath = os.path.dirname(os.path.realpath(__file__))
configFile = os.path.join(configPath, 'gtsnotifier_flask.cfg')
# Get the database location from the config file
config = ConfigParser.RawConfigParser()
config.read(configFile)
DATABASE = config.get('config', 'DATABASE')
PUSHAPPID = config.get('config', 'PUSHAPPID')
GTS_EMAIL = config.get('config', 'GTS_EMAIL')
GTS_EMAIL_PASS = config.get('config', 'GTS_EMAIL_PASS')

db = sqlite3.connect(DATABASE)
users = db.execute('select * from users').fetchall()

for user in users:
    # Store the columns in variables
    profileId, profAccountId, profSavedataId, dest, destType, timestamp = user

    # Construct the request header and data
    r_headers = {
        'Host': '3ds.pokemon-gl.com',
        'Connection': 'keep-alive',
        'Accept': 'application/json',
        'pragma': 'no-cache',
        'Origin': 'http://3ds.pokemon-gl.com',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': 'http://3ds.pokemon-gl.com/user/%s/gts/' % profileId,
        'Accept-Encoding': 'gzip,deflate,sdch',
    }
    data = {
        'languageId': '2',
        'memberSavedataIdCode': profileId,
        'accountId': profAccountId,
        'savedataId': profSavedataId,
        'count': '1'
    }

    r = requests.post(
        'http://3ds.pokemon-gl.com/frontendApi/mypage/getGtsTradeList',
        data,
        headers=r_headers
    )

    # Parse the json for the names of the pokemon and the time of the trade
    tradeData = r.json()
    recPoke = tradeData['tradeList'][0]['tradePokemon']['name']
    sentPoke = tradeData['tradeList'][0]['postSimple']['name']
    r_timestamp = tradeData['tradeList'][0]['tradeDate']
    message = 'Your ' + sentPoke + ' was successfully traded for ' + recPoke

    # timestamp = config.get('State', 'timestamp')
    # If the trade has not been notified already, send a notification
    if r_timestamp != timestamp:
        if destType == u'pushover':
            pushover_data = {
                'token': PUSHAPPID,
                'user': dest,
                'message': message,
            }
            requests.post(
                'https://api.pushover.net/1/messages.json',
                data=pushover_data
            )
        elif destType == u'email':
            msg = MIMEText(message)
            msg['Subject'] = message
            msg['From'] = GTS_EMAIL
            msg['To'] = dest
            s = smtplib.SMTP('smtp.gmail.com:587')
            s.ehlo()
            s.starttls()
            s.login(GTS_EMAIL, GTS_EMAIL_PASS)
            s.sendmail(GTS_EMAIL, dest, msg.as_string())
            s.quit()

        # Write the time of the last trade to the database
        db.execute(
            'update users set timestamp = ? where profileId = ?',
            (r_timestamp, profileId)
        )
        db.commit()

db.close()
