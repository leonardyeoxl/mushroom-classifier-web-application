import pytest
import requests
from collections import OrderedDict
import json
import os

host_ip = os.getenv('web_host_ip', "127.0.0.1")
port = int(os.getenv('web_port', 5000))

def test_prediction_history():

    payload = {
        "cap_shape": "sunken", 
        "cap_surface": "smooth", 
        "cap_color": "brown", 
        "bruises": "no", 
        "odor": "musty", 
        "gill_attachment": "notched",
        "gill_spacing": "crowded", 
        "gill_size": "narrow", 
        "gill_color": "brown", 
        "stalk_shape": "enlarging", 
        "stalk_root": "club", 
        "stalk_surface_above_ring": "smooth", 
        "stalk_surface_below_ring": "smooth", 
        "stalk_color_above_ring": "brown", 
        "stalk_color_below_ring": "brown", 
        "veil_type": "partial", 
        "veil_color": "brown", 
        "ring_number": "none", 
        "ring_type": "none", 
        "spore_print_color": "brown", 
        "population": "numerous", 
        "habitat": "meadows" 
    }
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

    r = requests.post("http://{}:{}/testclassify".format(host_ip, port), json=payload, headers=headers)
    print(r.status_code)
    assert r.status_code == 200
    assert r.json()['classifier_recv'] == "poisonous"

    r = requests.get("http://{}:{}/testpredictionhistory".format(host_ip, port))
    print(r.status_code)
    assert r.status_code == 200
    assert len(json.loads(r.json()['prediction_histories'])) == 1