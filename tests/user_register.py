import pytest
import requests
import os

host_ip = os.getenv('web_host_ip', "127.0.0.1")
port = int(os.getenv('web_port', 5000))

def test_register_different():
    payload = {'username': 'tester2', 'password': 'tester2'}
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    r = requests.post("http://{}:{}/doregister".format(host_ip, port), json=payload, headers=headers)
    print(r.status_code)
    assert r.status_code == 200
    print(r.json())
    assert r.json()['register_result'] == True

def test_register_same():
    payload = {'username': 'tester2', 'password': 'tester2'}
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    r = requests.post("http://{}:{}/doregister".format(host_ip, port), json=payload, headers=headers)
    print(r.status_code)
    assert r.status_code == 200
    print(r.json())
    assert r.json()['register_result'] == False