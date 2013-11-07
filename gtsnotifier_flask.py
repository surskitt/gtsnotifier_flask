#!/bin/env python

import sqlite3
import flask
from contextlib import closing
import requests
import ConfigParser

# configuration
config = ConfigParser.RawConfigParser()
config.read('/home/sharktamer/mysite/gtsnotifier_flask.cfg')
DATABASE = config.get('config', 'DATABASE')
DEBUG = config.getboolean('config', 'DEBUG')
SECRET_KEY = config.get('config', 'SECRET_KEY')
PUSHAPPID = config.get('config', 'PUSHAPPID')
# DATABASE = 'gtsnotifier_flask.db'
# # DATABASE = '/home/sharktamer/mysite/gtsnotifier_flask.db'
# DEBUG = False
# SECRET_KEY = 'pisspies'
# PUSHAPPID = 'axEnVejEhgH11pMZWrAdey9C66umz5'

# create the flask app object
app = flask.Flask(__name__)
app.secret_key = SECRET_KEY
app.debug = DEBUG


# Database connection helper function
def connect_db():
    return sqlite3.connect(DATABASE)


# This function can be imported and used to create the initial database schema
def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


# Decorator used to create a database object on a request
@app.before_request
def before_request():
    flask.g.db = connect_db()


# Decorator used to close the database connection after the request
@app.after_request
def after_request(response):
    flask.g.db.close()
    return response


# Render the home template when the base url is visited
@app.route('/')
def add_form():
    return flask.render_template('add_form.html')


# Check if the entered profile ID is in the database
def checkProfInDB(profId):
    profSearch = flask.g.db.execute(
        'select profileId from users where profileId = ?', (profId,))
    profSearchCount = len(profSearch.fetchall())
    return profSearchCount > 0


# Check if the entered profile ID is valid and public
def checkProfInvalid(profId):
    r = requests.get(
        'http://3ds.pokemon-gl.com/user/%s/gts/' % profId
    )
    # If the profile is invalid, the request is redirected to the gl homepage
    return r.url == 'http://3ds.pokemon-gl.com/'


# Check if the pushover user API entered is valid
def checkPushInvalid(pushId):
    pushover_data = {
        'token': 'axEnVejEhgH11pMZWrAdey9C66umz5',
        'user': pushId
    }
    r = requests.post(
        'https://api.pushover.net/1/users/validate.json',
        data=pushover_data
    )
    return r.status_code != 200


# view function for /add, the POST destination for the input form
@app.route('/add_user', methods=['POST'])
def add_user():

    # Store the form input in accessible variables
    profId = flask.request.form['inputProfileId']
    pushId = flask.request.form['inputPushoverUserAPI']

    # If either of the form inputs are blank...
    if '' in (profId, pushId):
        # Create a message to be sent along with the return request
        flask.flash('Please enter a valid profile ID', 'alert-danger')
    elif checkProfInDB(profId):
        flask.flash(
            'Your ID has already been added to the database',
            'alert-danger'
        )
    elif checkProfInvalid(profId):
        flask.flash(
            'Your profile ID is invalid or your gts trades are not visible',
            'alert-danger'
        )
    elif checkPushInvalid(pushId):
        flask.flash('Your pushover API is invalid', 'alert-danger')
    else:
        profile = requests.get(
            'http://3ds.pokemon-gl.com/user/%s/gts/' % profId
        )
        # Parse the user profile for account/savedata ids, for the gts request
        for line in profile.content.split('\n'):
            if 'USERS_ACCOUNT_ID' in line:
                profAccountId = line.split('\'')[1]
            elif 'USERS_SAVEDATA_ID' in line:
                profSavedataId = line.split('\'')[1]
        # Insert the form values and the requested values into users database
        flask.g.db.execute('insert into users values(?, ?, ?, ?, ?)', [
            profId,
            profAccountId,
            profSavedataId,
            pushId,
            0
        ])
        flask.g.db.commit()
        flask.flash(
            'Your profile was successfully added to the database',
            'alert-success'
        )
        # Send the user a success pushover notification
        pushover_data = {
            'token': PUSHAPPID,
            'user': pushId,
            'message': 'Your profile has been added successfully',
        }
        requests.post(
            'https://api.pushover.net/1/messages.json',
            data=pushover_data
        )

    # Return to the input form
    return flask.redirect(flask.url_for('add_form'))


@app.route('/remove')
def remove_form():
    return flask.render_template('remove_form.html')


@app.route('/remove_user', methods=['POST'])
def remove_user():

    # Store the form input in accessible variables
    profId = flask.request.form['inputProfileId']

    if not checkProfInDB(profId):
        flask.flash(
            'Your ID is not in the database',
            'alert-danger'
        )
    else:
        pushId = flask.g.db.execute(
            'select pushoverUserAPI from users where profileId = ?',
            (profId,)
            ).fetchone()[0]
        flask.g.db.execute('delete from users where profileId = ?', (profId,))
        flask.g.db.commit()
        flask.flash(
            'Your profile was successfully removed from the database',
            'alert-success'
        )
        pushover_data = {
            'token': PUSHAPPID,
            'user': pushId,
            'message': 'Your profile has been removed successfully',
        }
        requests.post(
            'https://api.pushover.net/1/messages.json',
            data=pushover_data
        )

    # Return to the remove form
    return flask.redirect(flask.url_for('remove_form'))


@app.route('/about')
def about_page():
    return flask.render_template('about.html')


@app.route('/contact')
def contact_page():
    return flask.render_template('contact.html')


@app.route('/help')
def help_page():
    return flask.render_template('help.html')

# Execute the script if it is run manually
if __name__ == '__main__':
    app.run()
