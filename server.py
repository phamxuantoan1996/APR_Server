#!/usr/bin/python3
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from threading import Thread
from mongDB import MongoDataBase
from logfile import LogFile
import json
import time


Pos_Idle1_Manual_Mode = "LM6"
Pos_Idle2_Manual_Mode = "LM5"
Pos_Idle_Auto_Mode = "LM4"
Pos_Warehouse = "LM5"

app = Flask(__name__)
CORS(app=app)

def task_chain_generate(task_list:list,apr_mode:str,line:int) -> list:
    try:
        task_chain = []
        if apr_mode == "Manual":
            call_machine = apr_db.MongoDB_find(collection_name="Call_Machine",query={"_id":int(task_list[0]["target_point"].split('e')[1])})
        else:
            call_machine = apr_db.MongoDB_find(collection_name="Call_Machine",query={"_id":line})
        point = call_machine[0]["point"]
        lift_level1 = call_machine[0]["lift_level1"]
        lift_level2 = call_machine[0]["lift_level2"]
        for task in task_list:
            if task["task_name"] == "pick":
                task_chain.append({"task_name":"pick","level_lift":lift_level2})
            elif task["task_name"] == "put":
                task_chain.append({"task_name":"put","level_lift":lift_level1})
            elif task["task_name"] == "navigation":
                task_chain.append({"task_name":"navigation_block","target_point":point})
            elif task["task_name"] == "warehouse":
                task_chain.append({"task_name":"navigation_block","target_point":Pos_Warehouse})
            elif task["task_name"] == "standby":
                if apr_mode == "Auto":
                    task_chain.append({"task_name":"navigation_block","target_point":Pos_Idle_Auto_Mode})
                elif apr_mode == "Manual":
                    amr_count = apr_db.MongoDB_find(collection_name="APR_Count",query={})
                    task_chain.append({"task_name":"navigation_block","target_point":Pos_Idle1_Manual_Mode})

        return task_chain
    except Exception as e:
        print("exception in generate task chain : ",str(e))
        return []

def send_task_chain_apr(task_chain:list) -> bool:
    check = apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1}, data = {"task_chain":task_chain})
    if check:
        check = apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"task_chain_status":0})
    return check
    
def task_auto_mode_func():
    while True:
        try:
            apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={"_id":1})[0]
            if apr_status["work_mode"] == "Manual" or apr_status["task_chain_status"] == 2:
                time.sleep(4)
                continue
            apr_missions = apr_db.MongoDB_find(collection_name="APR_Missions",query={})
            
            if len(apr_missions) > 0:
                if apr_missions[0]["mission_status"] == 1:
                    apr_db.MongoDB_update(collection_name="APR_Missions",query={"_id":apr_missions[0]["_id"]},data={"mission_status":2})
                    mission = {
                        "task_list" : [
                            {"task_name":"warehouse"},
                            {"task_name":"pick"},
                            {"task_name":"navigation","target_point":"line"+str(apr_missions[0]["line"])},
                            {"task_name":"put"},
                            {"task_name":"pick"},
                            {"task_name":"warehouse"},
                            {"task_name":"put"},
                            {"task_name":"standby"}
                        ],
                        "_id":apr_missions[0]["_id"]
                    }
                    task_chain = task_chain_generate(mission["task_list"],apr_mode="Auto",line=apr_missions[0]["line"])
                    if apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"mission_recv":mission,"task_chain":task_chain}):
                        apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"task_chain_status":0})

        except Exception as e:
            print("exception in task auto mode : ",str(e))
        
        time.sleep(2)

def readLogDB(date:str) -> list:
    logs = apr_db.MongoDB_find(collection_name="Logfile",query={"date":date})
    for i in range(0,len(logs)):
        logs[i].pop("_id")
    return logs

def deleteLogDB(date:str) -> int:
    num = apr_db.MongoDB_detele(collection_name="Logfile",data={"date":date})
    return num

# ---------------- API ---------------------------------------
@app.route('/status',methods=['GET'])
def get_status():
    try:
        apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={"_id":1})[0]
        call_machine = apr_db.MongoDB_find(collection_name="Call_Machine",query={})
        apr_status["call_machine"] = call_machine
        return jsonify(apr_status),200
    except Exception as e:
        return jsonify({"result":False,"desc":str(e)}),500

@app.route('/work_mode',methods=['POST'])
def apr_mode():
    try:
        # {"work_mode":0}
        content = request.json
        keys = content.keys()
        apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={"_id":1})[0]
        apr_task_chain_status = apr_status['task_chain_status']

        if 'work_mode' in keys and apr_task_chain_status != 2:
            mode = content['work_mode']
            if apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"work_mode":mode}):
                return jsonify({"result":True,"desc":""}),201
        return jsonify({"result":False,"desc":""}),200
    except Exception as e:
        print('send mode apr exception.')
        return jsonify({"result":False,"desc":str(e)}),500

@app.route('/task_chain',methods=['POST'])
def send_mission():
    try:
        content = request.json
        keys = content.keys()
        apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={"_id":1})[0]
        apr_mode = apr_status['work_mode']
        apr_task_chain_status = apr_status['task_chain_status']
        if "task_list" in keys and apr_mode == "Manual" and apr_task_chain_status != 2:
            task_chain = task_chain_generate(content["task_list"],apr_mode="Manual",line=None)
            if len(task_chain) > 0:
                if send_task_chain_apr(task_chain):
                    apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"mission_recv":content})
                    return jsonify({"result":True,"desc":""}),201
        return jsonify({"result":False,"desc":""}),200
    except Exception as e:
        return jsonify({"result":False,"desc":str(e)}),500

@app.route('/cancel',methods=['POST'])
def cancel_mission():
    try:
        apr_db.MongoDB_update(collection_name="APR_Status",query={"_id":1},data={"mission_recv":{},"signal_cancel":1,"task_chain":[],"task_index":0})
        return jsonify({"result":True}),201
    except Exception as e:
        return jsonify({"result":False,"desc":str(e)}),500
    
@app.route('/logs',methods = ['GET'])
def get_log():
    try:
        date = request.args.get("date")
        logs = readLogDB(date=date)
        return jsonify(logs),200
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.route('/logs',methods = ['DELETE'])
def delete_log():
    try:
        date = request.args.get("date")
        num = deleteLogDB(date=date)
        return jsonify({"result":num}),200
    except Exception as e:
        return jsonify({"error":str(e)}),500

# {
#     "line_activate" : [0,0,0,0,0,0,0,1,1]
# }
@app.route('/line_activate',methods = ['POST'])
def line_active():
    try:
        content = request.json
        if "line_activate" in content.keys():
            if len(content['line_activate']) == 8:
                apr_db.MongoDB_update(collection_name="APR_Status",query={'_id':1},data={'line_activate':content['line_activate']})
    except Exception as e:
        return jsonify({"error":str(e)}),500
# ------------------------------------------------------------
if __name__ == '__main__':

    log = LogFile(path_dir_log="Logfile")
    if log.init_logfile():
        log.writeLog(type_log="error",msg="APR Server Init")

    apr_db = MongoDataBase(database_name="APR_DB",collections_name=["Call_Machine","APR_Status","Locations","APR_Missions","APR_Count"])
    if apr_db.MongoDB_Init():
        print("MongoDB Init Success.")
    else:
        print("MongoDB Init Error")

    task_auto_mode = Thread(target=task_auto_mode_func,args=())
    task_auto_mode.start()

    app.run(host='0.0.0.0',port=8001,debug=False)
