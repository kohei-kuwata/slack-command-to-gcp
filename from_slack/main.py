import os
import json
import urllib.request
import urllib.parse
import googleapiclient.discovery

from flask import jsonify
from httplib2 import Http
from slack_sdk import WebClient
from slack.signature import SignatureVerifier
from google.cloud import pubsub_v1
from oauth2client.client import GoogleCredentials

PROJECT_ID = os.environ['PROJECT_ID']
TOPIC = os.environ['PUBSUB_TOPIC']
SLACK_TOKEN = os.environ['SLACK_TOKEN']
SLACK_SECRET = os.environ['SLACK_SECRET']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']

STATUS_LIST = ("status", "start", "stop")

json_open = open('instances.json', 'r')
instance_list = json.load(json_open)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC)

def verify_signature(request):
    request.get_data()
    verifier = SignatureVerifier(SLACK_SECRET)

    if not verifier.is_valid_request(request.data, request.headers):
        raise ValueError('Invalid request/credentials.')

def format_slack_message(msg):
    message = {
        'response_type': 'in_channel',
        'text': msg
    }

    return message

def check_param(text):
    params = {}

    param_arr = text.split('+')
    if len(param_arr) != 2:
        params["err_msg"] = "Need two argument"
        return params
    
    if not param_arr[0] in STATUS_LIST:
        msg = "1st argument: "
        for status in STATUS_LIST:
            msg += status + " "
        params["err_msg"] = "1st argument error\n" + msg
        return params
    
    target = param_arr[1]

    if not target in instance_list:
        params["err_msg"] = "2nd argument error\nPlease check instance name"
        return params

    params = {}
    params["command"] = param_arr[0]
    params["name"]    = target
    params["zone"]    = instance_list[target]["zone"]
    params["type"]    = instance_list[target]["type"]

    return params

def from_slack(request):
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    verify_signature(request)
    params_text = request.data.decode()

    params = params_text.split('&')
    param_dic = {}
    for param in params:
        param_tmp = param.split('=')
        param_dic[param_tmp[0]]  = param_tmp[1]
    
    pub_dic = check_param(param_dic["text"])
    
    if "err_msg" in pub_dic:
        return jsonify(format_slack_message(pub_dic["err_msg"]))
    
    res_text = "@" + param_dic["user_name"] \
               + " Start your request ( " + pub_dic["command"] + " " + pub_dic["name"] + " )"
    
    client = WebClient(token=SLACK_TOKEN)
    response = client.chat_postMessage(
        link_names = 1,
        channel = SLACK_CHANNEL,
        text = res_text
    )

    pub_dic["ts"] = response["ts"]
    pub_json = json.dumps(pub_dic)
    data = pub_json.encode()

    publisher.publish(topic_path, data=data)

    return ""
