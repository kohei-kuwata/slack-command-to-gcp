import os
import json
import time
import base64
import urllib.request

import googleapiclient.discovery
from oauth2client.client import GoogleCredentials
from httplib2 import Http
from urllib.parse import quote
from slack_sdk import WebClient

PROJECT_ID = os.environ['PROJECT_ID']
SLACK_TOKEN = os.environ['SLACK_TOKEN']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']

def post_slack(text, param):
    client = WebClient(token=SLACK_TOKEN)
    response = client.chat_postMessage(
        channel = SLACK_CHANNEL,
        text = text,
        thread_ts = param['ts']
    )

# To Compute Engine
def get_instances(service, project, zone, name):
    result = service.instances().get(project=project, zone=zone, instance=name).execute()
    return result

def start_instances(service, project, zone, name):
    result = service.instances().start(project=project, zone=zone, instance=name).execute()
    return result

def stop_instances(service, project, zone, name):
    result = service.instances().stop(project=project, zone=zone, instance=name).execute()
    return result

def operate_compute(http, param):
    compute = googleapiclient.discovery.build(
            'compute', 'v1',
            http = http,
            cache_discovery = False)
    
    zone = param['zone']
    name = param['name']

    instance_item = get_instances(compute, PROJECT_ID, zone, name)
    rtn_text = "Current Status: " + instance_item['status']
    post_slack(rtn_text, param)

    if param["command"] == "status":
        exit()
    elif param["command"] == "start":
        instance_item = start_instances(compute, PROJECT_ID, zone, name)
    elif param["command"] == "stop":
        instance_item = stop_instances(compute, PROJECT_ID, zone, name)

        loop_count = 0
        while instance_item['status'] != "TERMINATED":
            rtn_text = "sleep count: " + str(loop_count)
            post_slack(rtn_text, param)
            time.sleep(15)

            instance_item = get_instances(compute, PROJECT_ID, zone, name)
            rtn_text = "status: " + instance_item['status']
            post_slack(rtn_text, param)

            if loop_count == 10:
                rtn_text = "Stop your request. Please check the status of GCP instance"
                post_slack(rtn_text, param)
                break

            loop_count += 1
    
    rtn_text = "Your request done!\n" \
                + "status: " + instance_item['status']
    post_slack(rtn_text, param)

def from_pubsub(event, context):
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    param = json.loads(pubsub_message)

    credentials = GoogleCredentials.get_application_default()
    http = credentials.authorize(Http())

    if param['type'] == "compute":
        operate_compute(http, param)
