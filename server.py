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
Pos_Idle_Manual_Mode = "LM4"
Pos_Idle_Auto_Mode = "LM1"

app = Flask(__name__)
CORS(app=app)

def task_chain_generate(line:int,type_transfer:int,apr_mode:int) -> list:
    task_chain = []
    location = apr_db.MongoDB_find(collection_name="Locations",query={"_id":line})
    if len(location) > 0:
        task_chain.append({"task_name":"navigation_block","target_point":location[0]["point1"]})

        if type_transfer == 1:
            task_chain.append({"task_name":"put","lift_level":location[0]["lift_level2"]})
        elif type_transfer == 2:
            task_chain.append({"task_name":"put","lift_level":location[0]["lift_level2"]})
            task_chain.append({"task_name":"put","lift_level":location[0]["lift_level1"]})

        if apr_mode == 0:
            task_chain.append({"task_name":"navigation_block","target_point":Pos_Idle_Manual_Mode})
        elif apr_mode == 1:
            pass
    return task_chain

def check_call_request() -> list:
    line_active = apr_db.MongoDB_find(collection_name='APR_Status',query={'_id':1})[0]['line_active']
    line_request = []
    for request in Call_Request_List:
        if request['call_request'] > 0:
            line_request.append(request)
    return line_request

def send_task_chain_apr(task_chain:list) -> bool:
    check = apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1}, data = {"task_chain":task_chain})
    if check:
        check = apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"task_chain_status":0})
    return check
    
def task_auto_mode_func():
    while True:
        apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={})[0]
        if apr_status['mode'] == 0:
            time.sleep(5)
            continue
        line_call = check_call_request()
        
        time.sleep(2)
    
def task_poll_call_request_func() -> None:
    global Call_Request_List
    while True:
        Call_Request_List = apr_db.MongoDB_find(collection_name="Call_Machine",query={})
        for i in range(0,len(Call_Request_List)):
            Call_Request_List[i].pop('_id')
        time.sleep(2)

@app.route('/call_request',methods=['GET'])
def call_request():
    return jsonify(Call_Request_List),200

@app.route('/apr_mode',methods=['POST'])
def apr_mode():
    try:
        # {"mode":0}
        content = request.json
        keys = content.keys()
        apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={"_id":1})[0]
        apr_task_chain_status = apr_status['task_chain_status']

        if 'mode' in keys and apr_task_chain_status != 2:
            mode = int(content['mode'])
            if apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"mode":mode}):
                return jsonify({"result":True,"desc":""}),201
        return jsonify({"result":False,"desc":""}),200
    except Exception as e:
        print('send mode apr exception.')
        return jsonify({"result":False,"desc":str(e)}),500

    
@app.route('/send_mission',methods=['POST'])
def send_mission():
    try:
        # {'line':1,type:1}
        content = request.json
        keys = content.keys()
        apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={"_id":1})[0]
        apr_mode = apr_status['mode']
        
        apr_task_chain_status = apr_status['task_chain_status']
        if "line" in keys and 'type' in keys and apr_mode == 0 and apr_task_chain_status != 2:
            task_chain = task_chain_generate(line=content['line'],type_transfer=content['type'],apr_mode=0)
            if len(task_chain) > 0:
                if send_task_chain_apr(task_chain):
                    return jsonify({"result":True,"desc":""}),201
        return jsonify({"result":False,"desc":""}),200
    except Exception as e:
        return jsonify({"result":False,"desc":str(e)}),500
    

if __name__ == '__main__':

    log = LogFile(path_dir_log="Logfile")
    if log.init_logfile():
        log.writeLog(type_log="error",msg="APR Server Init")


    apr_db = MongoDataBase(database_name="APR_DB",collections_name=["Call_Machine","APR_Status","Locations"])
    if apr_db.MongoDB_Init():
        print("MongoDB Init Success.")
    else:
        print("MongoDB Init Error")
    
    task_poll_call_request = Thread(target=task_poll_call_request_func,args=())
    task_poll_call_request.start()

    task_auto_mode = Thread(target=task_auto_mode_func,args=())
    task_auto_mode.start()

    app.run(host='0.0.0.0',port=8002,debug=False)
