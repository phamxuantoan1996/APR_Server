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
    
def task_chain_generate(line:int,type:str,floor:int) -> list:
    task_chain = []
    location = apr_db.MongoDB_find(collection_name="Locations",query={"_id":line})
    if len(location) > 0:
        target_point = location[0]["point1"]
        lift_level = location[0]["lift_level" + str(floor)]
        task_chain.append({"task_name":"navigation_block","target_point":target_point})
        task_chain.append({"task_name":type,"lift_level":lift_level})
        task_chain.append({"task_name":"navigation_non_block","target_point":"LM1000"})
    return task_chain
    
@app.route('/send_mission',methods=['POST'])
def send_mission():
    try:
        content = request.json
        keys = content.keys()   
        if "line" in keys and "type" in keys and "floor" in keys:
            task_chain = task_chain_generate(line=content['line'],type=content['type'],floor=content['floor'])
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
        time.sleep(2)



if __name__ == '__main__':
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


    app.run(host='0.0.0.0',port=8002,debug=False)
