import pytest
import requests
from collections import OrderedDict
import json
import os

host_ip = os.getenv('web_host_ip', "127.0.0.1")
port = int(os.getenv('web_port', 5000))

def test_classify_poisonous():
    # x,y,w,t,p,f,c,n,n,e,e,s,s,w,w,p,w,o,p,n,s,u (test for poisonous)

    features_payload = {
        "cap_shape": "sunken", 
        "cap_surface": "smooth", 
        "cap_color": "purple", 
        "bruises": "no", 
        "odor": "spicy", 
        "gill_attachment": "notched",
        "gill_spacing": "crowded", 
        "gill_size": "narrow", 
        "gill_color": "purple", 
        "stalk_shape": "enlarging", 
        "stalk_root": "cup", 
        "stalk_surface_above_ring": "smooth", 
        "stalk_surface_below_ring": "smooth", 
        "stalk_color_above_ring": "brown", 
        "stalk_color_below_ring": "brown", 
        "veil_type": "universal", 
        "veil_color": "brown", 
        "ring_number": "none", 
        "ring_type": "sheathing", 
        "spore_print_color": "purple", 
        "population": "scattered", 
        "habitat": "urban" 
    }
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

    # payload = {'username': 'tester4', 'password': 'tester4'}
    # headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    # r = requests.post("http://{}:{}/doregister".format(host_ip, port), json=payload, headers=headers)
    # print(r.status_code)
    # assert r.status_code == 200
    # print(r.json())
    # assert r.json()['register_result'] == True

    # payload = {'username': 'tester4', 'password': 'tester4'}
    # headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    # r = requests.post("http://{}:{}/dologin".format(host_ip, port), json=payload, headers=headers)
    # print(r.status_code)
    # assert r.status_code == 200
    # print(r.json())
    # assert r.json()['login_result'] == True

    
    r = requests.post("http://{}:{}/classify".format(host_ip, port), json=features_payload, headers=headers)
    print(r.status_code)
    assert r.status_code == 200
    assert r.json()['classifier_recv'] == "poisonous"