from flask import Flask, flash, redirect, render_template, request, session, abort, jsonify
from redis import Redis
from collections import OrderedDict
import json
import logging
from logging import Formatter, FileHandler
import time
import os

host_ip = os.getenv('redis_host_ip', "127.0.0.1")
redis_port = int(os.getenv('redis_port', 6379))

app = Flask(__name__)
r = Redis(host=host_ip, port=redis_port, db=0)
logging.basicConfig(level=logging.DEBUG, filename='apiservice.log')
feature_mapping = dict()

def read_mapping():
    """Function reads in mapping.txt and creates a ordered dict of keys (feature) and values (corresponding options)
    """
    global feature_mapping

    with open('mapping.txt') as mappings_file:
        lines = mappings_file.readlines()

    mapping = OrderedDict()
    for line in lines:
        feature, feature_attrs = line.split(":")[0], line.split(":")[-1].replace(" ", "")
        feature_attr_mapping = OrderedDict()
        feature_attrs_list = feature_attrs.split(",")
        for feature_attr in feature_attrs_list:
            feature_attr_key = feature_attr.split("=")[0]
            feature_attr_val = feature_attr.split("=")[-1]
            feature_attr_mapping[feature_attr_key] = feature_attr_val.replace("\n", "")
        mapping[feature] = feature_attr_mapping

    feature_mapping = mapping

@app.route('/')
def Home():
    """Function checks if the user has logged in session
    
    Returns:
        Renders index.html template if user has no login session or runs GetPredictionHistory() function if user has login session
    """
    if not session.get('logged_in'):
        return render_template('index.html')
    else:
        return GetPredictionHistory()

@app.route('/register')
def Register():
    """Function that renders register.html template
    
    Returns:
        Renders register.html template
    """
    return render_template('register.html')

@app.route('/doregister', methods=['POST'])
def DoRegister():
    """Function gets the username and password. The user credentials are pushed into the redis mq. The result is recieved from the mq and checks if the user exists in the db
    
    Returns:
        If true, then session 'logged_in' stores True and Session 'uuid' stores uuid
        If false, then session 'logged_in' stores False
        [json] -- [Either {register_result:True} or {register_result:False}]
    """
    if request.is_json:
        app.logger.debug('is json')
        try:
            data = request.get_json()
            username = data['username']
            password = data['password']

            app.logger.debug(username)
            app.logger.debug(password)

            od = OrderedDict()
            od['username'] = username.strip()
            od['password'] = password.strip()

            r.rpush('user_register_request', json.dumps(od))

            while True:
                time.sleep(0)
                user_register_recieve = r.lpop('user_register_recieve')
                if user_register_recieve != None:
                    break

            user_register_recieve_result = user_register_recieve.decode().replace("\n", "")
            if user_register_recieve_result:
                session['logged_in'] = True
                session['uuid'] = user_register_recieve_result
                return jsonify(register_result=True)
            else:
                session['logged_in'] = False
                return jsonify(register_result=False)

        except Exception as e:
            app.logger.debug(e)
            return jsonify(register_result=False)
    else:
        app.logger.debug('is not json')

    return jsonify(register_result=False)

@app.route('/dologin', methods=['POST'])
def DoLogin():
    """Function gets the username and password. The credentials are pushed into the redis mq. The result is recieved from the mq and checks if the user exists in the db.
    
    Returns:
        If true, then session 'logged_in' stores True and Session 'uuid' stores uuid
        If false, then session 'logged_in' stores False
        [json] -- [Either {login_result:True} or {login_result:False}]
    """
    global r

    data = None
    if request.is_json:
        app.logger.debug('is json')
        try:
            data = request.get_json()
        except Exception as e:
            app.logger.debug(e)
    else:
        app.logger.debug('is not json')

    od = OrderedDict()
    od['username'] = data['username']
    od['password'] = data['password']

    r.rpush('user_login_request', json.dumps(od))

    try:
        while True:
            login_recieve = r.lpop('user_login_recieve')
            if login_recieve != None:
                break
        result = json.loads(login_recieve)['result']
        uuid = json.loads(login_recieve)['uuid']
        if result == True:
            session['logged_in'] = True
            session['uuid'] = uuid
            return jsonify(login_result=True)
        else:
            session['logged_in'] = False
            return jsonify(login_result=False)
    except Exception as e:
        app.logger.debug(e)
        return jsonify(login_result=False)

@app.route('/dologout', methods=['POST'])
def DoLogout():
    """Function performs log out
    
    Returns:
        session 'logged_in' stores False and Session 'uuid' stores empty string
    """
    session['logged_in'] = False
    session['uuid'] = ""
    return jsonify(logout_result=False)

@app.route('/dashboard', methods=['GET'])
def Dashboard():
    """Function checks if user is logged in and currates the features and their corresponding options
    
    Returns:
        If user logged in, renders dashboard.html template with the features and their corresponding options
        If user not logged in, runs Home() function
    """
    global feature_mapping

    if session.get('logged_in'):

        count = 0
        mapping = OrderedDict()
        mapping_row1 = OrderedDict()
        mapping_row2 = OrderedDict()
        mapping_row3 = OrderedDict()
        mapping_row4 = OrderedDict()
        for feature_mapping_key, feature_mapping_value in feature_mapping.items():

            feature_attr_mapping = list()
            for key, value in feature_mapping_value.items():
                feature_attr_mapping.append(key)
            mapping[feature_mapping_key] = feature_attr_mapping

            if count == 7:
                mapping_row1 = mapping
                mapping = OrderedDict()
            elif count == 14:
                mapping_row2 = mapping
                mapping = OrderedDict()
            elif count == 21:
                mapping_row3 = mapping
                mapping = OrderedDict()
            elif count == 22:
                mapping_row4 = mapping
                mapping = OrderedDict()

            count += 1

        return render_template('dashboard.html', mapping_row1=mapping_row1, mapping_row2=mapping_row2, mapping_row3=mapping_row3, mapping_row4=mapping_row4)
    
    else:

        return Home()

@app.route('/predictionhistory', methods=['GET'])
def GetPredictionHistory():
    """Function gets the user session uuid and pushes into the redis mq. When the results are recieved from the mq, the prediction histories is returned to the prediction_history.html template
    
    Returns:
        Renders prediction_history.html template with feature list and prediction histories
    """
    global feature_mapping

    r.rpush('prediction_history_request', session.get('uuid'))

    try:
        while True:
            prediction_history_receive = r.lpop('prediction_history_receive')
            if prediction_history_receive != None:
                break
    except Exception as e:
        app.logger.debug(e)
    
    feature_list = list()
    for feature_mapping_key, feature_mapping_value in feature_mapping.items():
        feature_list.append(feature_mapping_key)
    feature_list.append('Prediction')

    prediction_histories = json.loads(prediction_history_receive.decode())['prediction_histories']

    return render_template('prediction_history.html', feature_list=feature_list, prediction_histories=prediction_histories)

@app.route('/testpredictionhistory', methods=['GET'])
def TestGetPredictionHistory():
    """For Testing Purposes only
    
    Returns:
        [type] -- [description]
    """
    global feature_mapping

    r.rpush('prediction_history_request', "d8b274b0-6922-11ea-bc55-0242ac130003")

    try:
        while True:
            prediction_history_receive = r.lpop('prediction_history_receive')
            if prediction_history_receive != None:
                break
    except Exception as e:
        app.logger.debug(e)
    
    feature_list = list()
    for feature_mapping_key, feature_mapping_value in feature_mapping.items():
        feature_list.append(feature_mapping_key)
    feature_list.append('Prediction')

    prediction_histories = json.loads(prediction_history_receive.decode())['prediction_histories']

    app.logger.debug(prediction_histories)

    return jsonify(prediction_histories=json.dumps(prediction_histories))

@app.route('/classify', methods=['POST'])
def ClassifyRequest():
    """Function gets the options that the user has selected and pushes into the redis mq.
    
    Returns:
        edible or poisionous
    """
    global feature_mapping, r

    app.logger.debug('debugging')

    od = OrderedDict()
    app.logger.debug('od')
    data = None
    if request.is_json:
        app.logger.debug('is json')
        try:
            data = request.get_json()
        except Exception as e:
            app.logger.debug(e)
    else:
        app.logger.debug('is not json')
    
    if data != None:
        app.logger.debug('request.get_json()')
        od['cap-shape'] = feature_mapping['cap-shape'][data['cap_shape']]
        od['cap-surface'] = feature_mapping['cap-surface'][data['cap_surface']]
        od['cap-color'] = feature_mapping['cap-color'][data['cap_color']]
        od['bruises'] = feature_mapping['bruises'][data['bruises']]
        od['odor'] = feature_mapping['odor'][data['odor']]
        od['gill-attachment'] = feature_mapping['gill-attachment'][data['gill_attachment']]
        od['gill-spacing'] = feature_mapping['gill-spacing'][data['gill_spacing']]
        od['gill-size'] = feature_mapping['gill-size'][data['gill_size']]
        od['gill-color'] = feature_mapping['gill-color'][data['gill_color']]
        od['stalk-shape'] = feature_mapping['stalk-shape'][data['stalk_shape']]
        od['stalk-root'] = feature_mapping['stalk-root'][data['stalk_root']]
        od['stalk-surface-above-ring'] = feature_mapping['stalk-surface-above-ring'][data['stalk_surface_above_ring']]
        od['stalk-surface-below-ring'] = feature_mapping['stalk-surface-below-ring'][data['stalk_surface_below_ring']]
        od['stalk-color-above-ring'] = feature_mapping['stalk-color-above-ring'][data['stalk_color_above_ring']]
        od['stalk-color-below-ring'] = feature_mapping['stalk-color-below-ring'][data['stalk_color_below_ring']]
        od['veil-type'] = feature_mapping['veil-type'][data['veil_type']]
        od['veil-color'] = feature_mapping['veil-color'][data['veil_color']]
        od['ring-number'] = feature_mapping['ring-number'][data['ring_number']]
        od['ring-type'] = feature_mapping['ring-type'][data['ring_type']]
        od['spore-print-color'] = feature_mapping['spore-print-color'][data['spore_print_color']]
        od['population'] = feature_mapping['population'][data['population']]
        od['habitat'] = feature_mapping['habitat'][data['habitat']]
        od['uuid'] = session.get('uuid')
        app.logger.debug(session.get('uuid'))
        app.logger.debug('finish od')
    else:
        app.logger.debug('no request.get_json()')
    
    app.logger.debug(od)
    app.logger.debug(json.dumps(od))

    r.rpush('classifier_request', json.dumps(od))

    try:
        while True:
            classifier_recv = r.lpop('classifier_recieve')
            if classifier_recv != None:
                app.logger.debug(classifier_recv)
                app.logger.debug(jsonify(classifier_recv=classifier_recv.decode()))
                return jsonify(classifier_recv=classifier_recv.decode())
    except Exception as e:
        app.logger.debug(e)
        return jsonify(classifier_recv="Unable to classify")

@app.route('/testclassify', methods=['POST'])
def TestClassifyRequest():
    """For Testing Purposes only
    
    Returns:
        [type] -- [description]
    """
    global feature_mapping, r

    app.logger.debug('debugging')

    od = OrderedDict()
    app.logger.debug('od')
    data = None
    if request.is_json:
        app.logger.debug('is json')
        try:
            data = request.get_json()
        except Exception as e:
            app.logger.debug(e)
    else:
        app.logger.debug('is not json')
    

    if data != None:
        app.logger.debug('request.get_json()')
        od['cap-shape'] = feature_mapping['cap-shape'][data['cap_shape']]
        od['cap-surface'] = feature_mapping['cap-surface'][data['cap_surface']]
        od['cap-color'] = feature_mapping['cap-color'][data['cap_color']]
        od['bruises'] = feature_mapping['bruises'][data['bruises']]
        od['odor'] = feature_mapping['odor'][data['odor']]
        od['gill-attachment'] = feature_mapping['gill-attachment'][data['gill_attachment']]
        od['gill-spacing'] = feature_mapping['gill-spacing'][data['gill_spacing']]
        od['gill-size'] = feature_mapping['gill-size'][data['gill_size']]
        od['gill-color'] = feature_mapping['gill-color'][data['gill_color']]
        od['stalk-shape'] = feature_mapping['stalk-shape'][data['stalk_shape']]
        od['stalk-root'] = feature_mapping['stalk-root'][data['stalk_root']]
        od['stalk-surface-above-ring'] = feature_mapping['stalk-surface-above-ring'][data['stalk_surface_above_ring']]
        od['stalk-surface-below-ring'] = feature_mapping['stalk-surface-below-ring'][data['stalk_surface_below_ring']]
        od['stalk-color-above-ring'] = feature_mapping['stalk-color-above-ring'][data['stalk_color_above_ring']]
        od['stalk-color-below-ring'] = feature_mapping['stalk-color-below-ring'][data['stalk_color_below_ring']]
        od['veil-type'] = feature_mapping['veil-type'][data['veil_type']]
        od['veil-color'] = feature_mapping['veil-color'][data['veil_color']]
        od['ring-number'] = feature_mapping['ring-number'][data['ring_number']]
        od['ring-type'] = feature_mapping['ring-type'][data['ring_type']]
        od['spore-print-color'] = feature_mapping['spore-print-color'][data['spore_print_color']]
        od['population'] = feature_mapping['population'][data['population']]
        od['habitat'] = feature_mapping['habitat'][data['habitat']]
        od['uuid'] = "d8b274b0-6922-11ea-bc55-0242ac130003"
        app.logger.debug(session.get('uuid'))
        app.logger.debug('finish od')
    else:
        app.logger.debug('no request.get_json()')
    
    app.logger.debug(od)
    app.logger.debug(json.dumps(od))

    r.rpush('classifier_request', json.dumps(od))

    try:
        while True:
            classifier_recv = r.lpop('classifier_recieve')
            if classifier_recv != None:
                app.logger.debug(classifier_recv)
                app.logger.debug(jsonify(classifier_recv=classifier_recv.decode()))
                return jsonify(classifier_recv=classifier_recv.decode())
    except Exception as e:
        app.logger.debug(e)
        return jsonify(classifier_recv="Unable to classify")

if __name__ == "__main__":
    read_mapping()
    app.secret_key = os.urandom(12)
    app.run(host="0.0.0.0", port=5000, debug=True)