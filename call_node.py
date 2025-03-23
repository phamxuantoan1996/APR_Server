#!/usr/bin/python3
import socket
from threading import Thread
from mongDB import MongoDataBase

import json
import time

Call_Addr_List = []
Call_Response_List = []

class Call_Loader:
    def __init__(self,ip:str):
        self.__call_ip = ip
        self.__call_request = -1
        self.__call_response = -1

    @property
    def call_ip(self) -> str:
        return self.__call_ip
    @call_ip.setter
    def call_ip(self,ip:str):
        self.__call_ip = ip
    
    @property
    def call_response(self) -> int:
        return self.__call_response
    @call_response.setter
    def call_response(self,val:int):
        self.__call_response = val

    @property
    def call_request(self) -> int:
        return self.__call_request
    @call_request.setter
    def call_request(self,val:int):
        self.__call_request = val

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
    global Call_Response_List
    index = 0
    for call in Call_Response_List:
        if call['call_addr'] == addr[0]:
            break
        index = index + 1
    while True:
        recv_data = ''
        try:
            recv_data = c.recv(1024)
            # print(recv_data)
            if len(recv_data) == 0:
                break
            else:
                recv_data_string = recv_data.decode('utf-8').split('}')[0] + '}'
                json_data_dict = json.loads(recv_data_string)
                # {"call":1}
                print(addr[0]," : ",json_data_dict," : ",index)
                keys = json_data_dict.keys()
                if "call" in keys:
                    try:
                        val = int(json_data_dict['call'])
                        apr_db.MongoDB_update(collection_name="Call_Signal_Request",query={"call_addr":str(addr[0])},data={"call_request":val})
                        response = Call_Response_List[index]['call_response']
                        print(response)
                        c.send(json.dumps({"response":response}).encode('utf-8'))
                        continue
                    except Exception as e:
                        print('exception : call signal request')
                print('call signal data is not valid.')
        except Exception as e:
            print("exception recv data")
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
            Call_Addr_List.append(addr[0])
            task_client = Thread(target=task_poll_call_func,args=(c,addr))
            task_client.start()
        time.sleep(2)

def task_poll_call_response_func():
    global Call_Response_List
    while True:
        Call_Response_List = apr_db.MongoDB_find(collection_name="Call_Signal_Response",query={})
        time.sleep(1)

if __name__ == '__main__':
    
    apr_db = MongoDataBase(database_name="APR_DB",collections_name=["Call_Signal_Request","Call_Signal_Response"])

    if apr_db.MongoDB_Init():
        print("MongoDB Init Success.")
    else:   
        print("MongoDB Init Error.")

    server_call = Server_Call(host='192.168.68.121',port=5000,timeout=60,max_client=8)
    server_call.server_call_start()

 
    task_server_call = Thread(target=task_server_call_func,args=())
    task_server_call.start()

    task_poll_call_response = Thread(target=task_poll_call_response_func,args=())
    task_poll_call_response.start()

    

    


    
