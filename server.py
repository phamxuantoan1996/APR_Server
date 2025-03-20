#!/usr/bin/python3
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from threading import Thread
from mongDB import MongoDataBase
from logfile import LogFile
import json
import time

Call_Request_List = []

app = Flask(__name__)
CORS(app=app)

def task_chain_generate(line:int) -> list:
    task_chain = []
    location = apr_db.MongoDB_find(collection_name="Locations",query={"_id":line})
    if len(location) > 0:
        task_chain.append({"task_name":"navigation_block","target_point":location[0]["point1"]})
        task_chain.append({"task_name":"put","lift_level":location[0]["lift_level2"]})
        task_chain.append({"task_name":"put","lift_level":location[0]["lift_level1"]})
        task_chain.append({"task_name":"navigation_non_block","target_point":"LM1000"})
    return task_chain

def check_call_request() -> bool:
    for request in Call_Request_List:
        if request['call_line'] > 0:
            return True
    return False

def send_task_chain_apr(task_chain:list) -> bool:
    url_post = "http://127.0.0.1:8001/task_chain"
    data = {"task_chain":task_chain}
    try:
        response = requests.post(url=url_post,json=data)
        if response.status_code == 201:
            return True
        else:
            return False
    except Exception as e:
        print(str(e))
        return False
    
@app.route('/call_request',methods=['GET'])
def call_request():
    return jsonify(Call_Request_List),200

@app.route('/confirm_complete',methods=['POST'])
def confirm_complete():
    try:
        content = request.json
        if "confirm" in content.keys():
            if content['confirm']:
                return jsonify({"result":True}),201
            return jsonify({"result":False}),200
    except Exception as e:
        return jsonify({"result":False,"desc":str(e)}),500

@app.route('/call_response',methods=['POST'])
def call_reponse():
    try:
        content = request.json
        keys = content.keys()
        if 'call_line' in keys and 'call_response' in keys:
            line = content['call_line']
            response = content['call_response']
            apr_db.MongoDB_update(collection_name="Call_Signal_Response",query={"call_line":line},data={"call_response":response})
        return jsonify({"result":True,"desc":""}),201
    except Exception as e:
        return jsonify({"result":False,"desc":str(e)}),500
    
@app.route('/send_mission',methods=['POST'])
def send_mission():
    try:
        content = request.json
        keys = content.keys()
        if "line":
            task_chain = task_chain_generate(line=content['line'])
            if len(task_chain) > 0:
                if send_task_chain_apr(task_chain):
                    return jsonify({"result":True,"desc":""}),201
            return jsonify({"result":False,"desc":""}),200
    except Exception as e:
        return jsonify({"result":False,"desc":str(e)}),500
    
def task_poll_call_request_func() -> None:
    global Call_Request_List
    while True:
        Call_Request_List = apr_db.MongoDB_find(collection_name="Call_Signal_Request",query={})
        for i in range(0,len(Call_Request_List)):
            Call_Request_List[i].pop('_id')
        if check_call_request():
            pass
        time.sleep(2)

def task_poll_agf_status_func():
    while True:
        url_get = "http://127.0.0.1:8001/status"
        try:
            response = requests.get(url=url_get)
            if response.status_code == 200:
                APR_Status = json.loads(response.content.decode('utf-8'))
                print(APR_Status)
                
        except Exception as e:
            print(str(e))
        time.sleep(1)



if __name__ == '__main__':
    APR_Status = {
        "src_status":[],
        "task_chain":[],
        "cancel_signal":False,
        "pause_signal":False,
        "mission_status":0
    }

    log = LogFile(path_dir_log="Logfile")
    if log.init_logfile():
        log.writeLog(type_log="error",msg="APR Server Init")


    apr_db = MongoDataBase(database_name="APR_DB",collections_name=["Call_Signal_Request","Call_Signal_Response","Locations"])
    if apr_db.MongoDB_Init():
        print("MongoDB Init Success.")
    else:
        print("MongoDB Init Error")
    
    task_poll_call_request = Thread(target=task_poll_call_request_func,args=())
    task_poll_call_request.start()

    task_poll_agf_status = Thread(target=task_poll_agf_status_func,args=())
    task_poll_agf_status.start()


    app.run(host='0.0.0.0',port=8002,debug=False)
