import logging
from logging.handlers import TimedRotatingFileHandler
import os

class LogFile:
    def __init__(self,path_dir_log:str) -> None:
        self.path = path_dir_log
    
    def init_logfile(self) -> bool:
        try:
            if not os.path.exists(self.path):
                os.mkdir(self.path)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s : %(message)s")
            self.logger = logging.getLogger('werkzeug')
            self.logger.setLevel(logging.ERROR)
            handler = TimedRotatingFileHandler(filename=self.path + "/logfile" + ".log",when="midnight", backupCount=30)
            handler.suffix = "%Y%m%d"
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            return True
        except Exception as e:
            print(e)
            return False
    
    def writeLog(self,type_log:str,msg:str):
        try:
            if type_log == 'error':
                self.logger.error(msg)  
            elif type_log == 'info':
                self.logger.info(msg)  
        except Exception as e:
            print(e)
