from CassandraDatabase import CassandraDatabase
import string
import json
from collections import OrderedDict
import joblib
import pandas as pd
from redis import Redis
import logging
import numpy as np
from numpy import array
from numpy import argmax
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
import time
import os

logging.basicConfig(level=logging.DEBUG, filename='databasehelper.log')
casssandra_db = None

def read_labels():
    """Reads the labels and convert to a json dictionary
    
    Returns:
        [dict] -- {0:poisonous, 1:edible}
    """
    with open('/model/labels.txt') as labels_file:
        lines = labels_file.readlines()

    labels_dict = dict()
    index = 0
    for label in lines:
        labels_dict[index] = label
        index += 1

    return labels_dict

def classify(classifier_request, labels):
    """Function performs classification from the options that the user has selected and the loaded model. 
    
    Arguments:
        classifier_request {[string]} -- contains user selected options and user uuid
        labels {[dict]} -- contains {0:poisonous, 1:edible}
    
    Returns:
        [String] -- predicted classification
    """
    global casssandra_db

    classifier_request_dict = json.loads(classifier_request, object_pairs_hook=OrderedDict)
    user_uuid = classifier_request_dict['uuid']
    del classifier_request_dict['uuid']
    features = classifier_request_dict
    features = dict(features)
    
    features_df = pd.DataFrame.from_dict(features, orient='index').transpose()

    with open('mapping.txt') as mappings_file:
        lines = mappings_file.readlines()

    outer_list = list()
    for line in lines:
        feature, feature_attrs = line.split(":")[0], line.split(":")[-1].replace(" ", "")
        feature_attrs_list = feature_attrs.split(",")
        inner_list = list()
        for feature_attr in feature_attrs_list:
            feature_attr_val = feature_attr.split("=")[-1].replace("\n", "")
            inner_list.append(feature_attr_val)
        outer_list.append(inner_list)

    enc = outer_list

    # one hot encoding
    ohe = OneHotEncoder(categories=enc, handle_unknown='ignore', sparse=False)
    colnames= ['{}_{}'.format(col,val) for col,unique_values in zip(features_df.columns, ohe.categories) \
                                       for val in unique_values]
    features_df = pd.DataFrame(ohe.fit_transform(features_df), columns=colnames) 

    # load model
    loaded_model = joblib.load('/model/mushroom_classifier_march_2020.sav')

    # make prediction
    prediction = loaded_model.predict(features_df.to_numpy().reshape(1,-1))
    prediction = labels[prediction.tolist()[0]].replace("\n", "")
    logging.debug(prediction)

    # save predictions and user options in db
    casssandra_db.CassandraStorePredictions(user_uuid, features, prediction)

    return prediction


def Main(labels):
    global casssandra_db

    redis_host_ip = os.getenv('redis_host_ip', "127.0.0.1")
    redis_port = int(os.getenv('redis_port', 6379))

    logging.debug("starting main")
    r = Redis(host=redis_host_ip, port=redis_port, db=0, health_check_interval=30)
    logging.debug("connected to redis server")
    casssandra_db = CassandraDatabase()

    prediction = None
    while True:
        
        # User Register Request
        user_register_request = r.lpop('user_register_request')
        if user_register_request != None:
            logging.debug("recieved user register request")
            user_credentials = json.loads(user_register_request, object_pairs_hook=OrderedDict)
            user_credentials = dict(user_credentials)
            register_status, register_result = casssandra_db.CassandraRegisterUser(user_credentials)
            if register_status == "True":
                logging.debug("User Register TRUE")
                r.rpush('user_register_recieve', str(register_result))
            else:
                logging.debug("User Register FALSE")
                r.rpush('user_register_recieve', "")

        # User Login Request
        user_login_request = r.lpop('user_login_request')
        if user_login_request != None:
            logging.debug("recieved user login request")
            user_credentials = json.loads(user_login_request, object_pairs_hook=OrderedDict)
            user_credentials = dict(user_credentials)
            login_status, login_result = casssandra_db.CassandraCheckLoginCredentials(user_credentials)
            if login_status == "True":
                logging.debug("User Login TRUE")
                r.rpush('user_login_recieve', json.dumps(dict(result=True, uuid=str(login_result))))
            else:
                logging.debug("User Login FALSE")
                r.rpush('user_login_recieve', json.dumps(dict(result=False, uuid=None)))

        # Classifier Request
        classifier_request = r.lpop('classifier_request')
        if classifier_request != None:
            logging.debug("recieved classifer request")
            prediction = classify(classifier_request, labels)
            r.rpush('classifier_recieve', prediction)

        # Prediction History Request
        prediction_history_request = r.lpop('prediction_history_request')
        if prediction_history_request != None:
            logging.debug("recieved prediction history request")
            user_uuid = prediction_history_request.decode()
            prediction_histories = casssandra_db.CassandraRetrievePredictionHistory(user_uuid)
            r.rpush('prediction_history_receive', json.dumps(dict(prediction_histories=prediction_histories)))

if __name__ == "__main__":
    labels = read_labels()
    Main(labels)