import threading 
import multiprocessing
import sys
import os
import requests
import RPi.GPIO as GPIO 
import logging
import requests
import json

class pinMonitor():
    def __init__(self, printer_api, switch_pin):
        self.switch_pin = switch_pin
        self.threadID = "pin_monitor"
        self.api_key = printer_api
        self.paused = False
        self.counter1 = 0
        self.counter0 = 0
        self.lock_1_timer = False
        self.parent, self.child = multiprocessing.Pipe()
        self.monitor = None
        logging.basicConfig(filename='/home/pi/.octoprint/logs/octoprint.log', level=logging.DEBUG)
        self.logger = logging
        self.exit = False

    def stop_monitor(self):
        #self.logger.info("Stopping monitor! ########################")
        self.parent.send({'exit':True})
        if self.monitor != None:
            for child in multiprocessing.active_children():
                self.logger.info("Killed Child")
                child.terminate()

    def start_monitor(self):
        #self.logger.info("Starting monitor! ########################")
        self.monitor = multiprocessing.Process(target=self.run_monitor, args=(self.child,))
        self.monitor.start()

    def monitor_pipe(self):
        poll = self.parent.poll()
        if poll:
            data = self.parent.recv()
            if data:
                self.logger.info(str(data) + "###########")
                return data
                
        return False
        

    def run_monitor(self, child_pipe):
        self.initialize_pin()
        self.monitor_pin(child_pipe)

    def initialize_pin(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.switch_pin, GPIO.IN, GPIO.PUD_UP)

    def monitor_pin(self, child):
        
        while not self.paused and not self.exit:
            #check to see if we need to exit 
            poll = child.poll()
            if poll:
                data = child.recv()
                if 'exit' in data:
                    if data['exit']:
                        self.exit = True
                        continue

            #check the state of the pin
            state = GPIO.input(21)
            if state ==1:
                self.counter1 +=1

                if not self.lock_1_timer:
                    self.lock_1_timer = True
                    t = threading.Timer(10.0, self.check_count,args=(self.counter1,))
                    t.start()

        #self.logger.info("While looped Stopped #################")
        #Stop the print
        if self.paused:
            header = {'Content-Type': 'application/json', 'X-Api-Key': self.api_key}
            payload = {'command': 'pause','action': 'pause'}
            url = "http://127.0.0.1/api/job"
            
            r = requests.post(url, headers=header, data=json.dumps(payload))
            #self.logger.info(r.text)
            child.send(True)
        elif self.exit:
            self.logger.info("Process " + str(os.getpid()) +" Exiting" )
            sys.exit()
            
    def check_count(self, original_count):
        #self.logger.info("Checking Count " + str(self.counter1 - original_count) + " ###################################")
        if self.counter1 - original_count > 100000:
            #self.logger.info("Pausing the Print!")
            self.paused = True
            
        else:
            self.lock_1_timer = False
        
        

