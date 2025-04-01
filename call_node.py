#!/usr/bin/python3
import socket
from threading import Thread
from mongDB import MongoDataBase

import json
import time
import random

Call_Addr_List = []
apr_status = {}

class Server_Call:
    def __init__(self,host:str,port:int,timeout:int,max_client:int) -> None:
        self.__server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.__server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.__host = host
        self.__port = port
        self.__timeout = timeout
        self.__max_client = max_client
    def server_call_start(self) -> bool:
        try:
            self.__server.bind((self.__host,self.__port))
            self.__server.listen(self.__max_client)
            return True
        except Exception as e:
            print("Server call amr start error : " + str(e))
            return False
    @property
    def server(self) -> socket.socket:
        return self.__server

def task_poll_call_func(c : socket.socket,addr):
    c.settimeout(20)
    recv_string_total = ''
    while True:
        try:
            recv_data = c.recv(1024)
            if len(recv_data) == 0:
                break
            else:
                recv_string = recv_data.decode('utf-8')
                if '/' in recv_string:
                    temp = recv_string.split('/')[0]
                    recv_string_total = recv_string_total + temp
                else:
                    recv_string_total = recv_string_total + recv_string
                    continue
                # print(recv_string_total)
                json_data_dict = json.loads(recv_string_total)
                # print(json_data_dict)
                
                keys = json_data_dict.keys()
                if "Call ID" in keys and "button" in keys and "input" in keys:
                    try:
                        machine = apr_db.MongoDB_find(collection_name="Call_Machine",query={"ip_address":str(addr[0])})[0]
                        if apr_status["line_activate"][machine["_id"] - 1] == 0:
                            break
                        floor1 = 0
                        floor2 = 0
                        output = []
                        for btn in json_data_dict['button']:
                            if btn["status"]:
                                output.append(1)
                            else:
                                output.append(0)
                        for input in json_data_dict['input']:
                            if input["id"] == 0:
                                if input['status']:
                                    floor1 = 1
                                else:
                                    floor1 = 0
                            elif input["id"] == 1:
                                if input['status']:
                                    floor2 = 1
                                else:
                                    floor2 = 0

                        if machine['floor1'] != floor1:
                            mission = apr_db.MongoDB_find(collection_name="APR_Missions",query={"ip_address":str(addr[0])})
                            if floor1 == 0 and len(mission) > 0:
                                if mission[0]["mission_status"] == 1:
                                    apr_db.MongoDB_detele(collection_name="APR_Missions",data={"ip_address":str(addr[0])})
                            elif floor1 == 1 and len(mission) == 0:
                                apr_db.MongoDB_insert(collection_name="APR_Missions",data={"line":1,"mission_status":1,"ip_address":str(addr[0]),"_id":random.randint(0,9999999999)})
                        apr_db.MongoDB_update(collection_name="Call_Machine",query={"ip_address":str(addr[0])},data={"floor1":floor1,"floor2":floor2,"response_transfer":output})
                        c.send(json.dumps({"output":machine["request_transfer"]}).encode('utf-8'))
                    except Exception as e:
                        print('exception : call signal : ',str(e))
                recv_string_total = ''
        except Exception as e:
            print("exception recv data : ",str(e))
            break
    apr_db.MongoDB_update(collection_name="Call_Machine",query={"ip_address":str(addr[0])},data={"floor1":-1,"floor2":-1,"response_transfer":-1})
    mission = apr_db.MongoDB_find(collection_name="APR_Missions",query={"ip_address":str(addr[0])})
    if len(mission) > 0:
        if mission[0]["mission_status"] != 2:
            apr_db.MongoDB_detele(collection_name="APR_Missions",data={"ip_address":str(addr[0])})
        
    print('client : ' + str(addr) + ' closed!')
    Call_Addr_List.remove(addr[0])
    c.close()

def task_server_call_func():
    while True:
        c,addr = server_call.server.accept()
        print('address : ' + str(addr))
        try:
            Call_Addr_List.index(addr[0])
        except Exception as e:
            line_activate = apr_status["line_activate"]
            
            call_machines = apr_db.MongoDB_find(collection_name="Call_Machine",query={"ip_address":addr[0]})
            if len(call_machines) == 0:
                c.close()
                continue
            call_machine = call_machines[0]
            
            id = call_machine["_id"]
            if line_activate[id-1] == 0:
                c.close()
                continue
            Call_Addr_List.append(addr[0])
            task_client = Thread(target=task_poll_call_func,args=(c,addr))
            task_client.start()
        time.sleep(2)

def task_apr_status_poll_func():
    global apr_status
    while True:
        apr_status = apr_db.MongoDB_find(collection_name="APR_Status",query={"_id":1})[0]
        time.sleep(2)

if __name__ == '__main__':
    
    apr_db = MongoDataBase(database_name="APR_DB",collections_name=["APR_Status","Call_Machine","APR_Missions"])

    apr_db.MongoDB_update(collection_name="Call_Machine",query={},data={"request_transfer":[0,0,0,0]})

    if apr_db.MongoDB_Init():
        print("MongoDB Init Success.")
    else:   
        print("MongoDB Init Error.")

    server_call = Server_Call(host='192.168.110.10',port=5000,timeout=60,max_client=8)
    server_call.server_call_start()

    task_server_call = Thread(target=task_server_call_func,args=())
    task_server_call.start()

    task_agf_status_poll = Thread(target=task_apr_status_poll_func,args=())
    task_agf_status_poll.start()

    

    


    
