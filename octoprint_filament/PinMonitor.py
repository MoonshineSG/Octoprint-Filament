import threading 
import multiprocessing
import sys
import os
import requests
import RPi.GPIO as GPIO 
import logging
import requests
import json
import time

class pinMonitor():
    def __init__(self, printer_api, switch_pin, pin_timer=False, **kwargs):
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
        self.pin_timer = pin_timer
        self.timer_done = False
        self.one_minute_timer = True

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
                self.logger.info(str(data) + " Pin Monitor Data ###########")
                return data
                
        return False
        

    def run_monitor(self, child_pipe):
        self.initialize_pin()
        self.monitor_pin(child_pipe)

    def initialize_pin(self):
        self.logger.info("Process " + str(os.getpid()) +" Starting for Pin Monitor" )
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.switch_pin, GPIO.IN, GPIO.PUD_UP)

    def monitor_pin(self, child):
        if self.pin_timer:
            self.logger.info("Five Minute Timer loop Started #################")
            timer = int(round(time.time()*1000))
            timer += 300000
            self.timer_done = False
            update_time = timer + 1000
            while not self.timer_done and not self.exit:
                cur_time = int(round(time.time()*1000))
                
                if cur_time >= timer:
                    self.timer_done = True
                if cur_time >= update_time:
                    update_time = cur_time + 1000
                    self.logger.info(str(cur_time) + " " + str(timer))
    
            self.logger.info("Five Minute Timer loop Stopped #################")
        
        self.logger.info("Pin Monitor Started #################")
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
            self.counter0 = 0
            self.counter1 = 0
            
            state = GPIO.input(self.switch_pin)
            if state ==1:

                #set timer
                timer = int(round( time.time() *1000) )
                timer += 15000 #15 seconds
                self.timer_done = False
                #reset counters
                self.counter0 = 0
                self.counter1 = 0
                stime = time.time()
                self.logger.info("Timer Loop Started")
                while int(round( time.time() *1000) ) < timer:
                    state = GPIO.input(self.switch_pin)
                    if state == 1:
                        self.counter1 += 1
                    elif state == 0:
                        self.counter0 += 1
                etime = time.time() - stime
                self.logger.info("Timer Loop Ended " + str(etime))

                total = self.counter0 + self.counter1
                self.logger.info("Total: " + str(total) + " 1s: " + str(self.counter1) + " 0s: " + str(self.counter0))

                p1 = 0
                p0 = 0
                if self.counter1 >= 1:
                    p1 = float((float(self.counter1) / float(total)) * 100.00)
                    p0 = float((float(self.counter0) / float(total)) * 100.00)
                

                self.logger.info("1 Percentage: " + str(p1))
                self.logger.info("0 Percentage: " + str(p0))

                #if the 1s are over 80 percent of the total then pause
                if int(p1) > 80:
                    self.logger.info("Pausing")
                    self.paused = True
                    break



               

        self.logger.info("pin monitor Stopped #################")
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
            
    
        
        

