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
from datetime import datetime

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
        logging.basicConfig(filename='/home/pi/.octoprint/logs/octoprint.log', level=logging.INFO)
        self.logger = logging
        self.exit = False
        self.pin_timer = pin_timer
        self.timer_done = False
        self.logger.info("Pin Monitor made with api key: " + str(self.api_key))

    def update_API_key_and_pin_timer(self, new_key, timer=False):
        self.api_key = new_key
        self.pin_timer = timer

    def stop_monitor(self):
        
        self.parent.send({'exit':True})
        self.logger.info("Stopping monitor! ########################")
        for child in multiprocessing.active_children():
            if child.is_alive():
                self.logger.info("Killing child")
                child.join(5)                
                self.logger.info("Joined Child with pid: " + str(child.pid))
                child.terminate()
                self.logger.info("Child's Exit Code is: " + str(child.exitcode))
            else:
                self.logger.info("Child with pid: " + str(child.pid) + " is not alive")
                self.logger.info("Child's Exit Code is: " + str(child.exitcode))
            # child.terminate()
            # self.logger.info("Killed Child at PID: " + str(child.pid))

    def start_monitor(self):
        self.parent, self.child = multiprocessing.Pipe()
        self.monitor = multiprocessing.Process(target=self.run_monitor, args=(self.child,), name="Filament_Sensor")
        self.logger.info("Starting monitor! ########################")
        self.monitor.start()
        self.logger.info("Process " + str(self.monitor.pid) +" is assigned to the pin monitor." )
        self.parent.send({'start':True})
        self.parent.send({'ack_alive': True})
        

    def monitor_pipe(self):
        poll = self.parent.poll()
        if poll:
            data = self.parent.recv()
            if data:
                self.logger.info(str(data) + " Pin Monitor Data ###########")
                return data

        return False

    def run_monitor(self, child_pipe):
        self.logger.info("Process " + str(os.getpid()) +" Starting for Pin Monitor" )

        self.logger.info("Flushing Monitor")
        self.accept_flush(child_pipe)

        self.logger.info("Initializing Pin")
        self.initialize_pin()

        self.logger.info("Running Failsafe")
        self.start_gcode_failsafe(child_pipe)

        self.logger.info("Starting Monitor")
        self.monitor_pin(child_pipe)

        self.logger.info("Returning Results")
        self.run_results(child_pipe)
        self.logger.info("Finished monitor loop")

    def accept_flush(self, child_pipe):
        start_process = False
        while not start_process:
            poll = child_pipe.poll()
            if poll:
                data = child_pipe.recv()
                if 'start' in data and data['start'] == True:
                    start_process = True
                    break

        return


    def initialize_pin(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.switch_pin, GPIO.IN, GPIO.PUD_UP)

    def monitor_pin(self, child):
        self.logger.info("Pin Monitor Started #################")
        while not self.paused and not self.exit:
            self.exit_switch(child)
            if self.exit: 
                continue
            #check the state of the pin
            self.counter0 = 0
            self.counter1 = 0
            state = GPIO.input(self.switch_pin)
            if state ==1:
                #set timer
                timer_15s = self.timer(15)
                self.counter0 = 0
                self.counter1 = 0
                while not next(timer_15s) and not self.exit:
                    self.exit_switch(child)
                    if self.exit: 
                        break
                    state = GPIO.input(self.switch_pin)
                    if state == 1:
                        self.counter1 += 1
                    elif state == 0:
                        self.counter0 += 1
                # Calculate confidence interval
                total = self.counter0 + self.counter1
                self.logger.info("Total: " + str(total) + " 1s: " + str(self.counter1) + " 0s: " + str(self.counter0))
                p1 = 0
                p0 = 0
                if self.counter1 >= 1:
                    p1 = float((float(self.counter1) / float(total)) * 100.00)
                    p0 = float((float(self.counter0) / float(total)) * 100.00)

                self.logger.info("1 Percentage: " + str("{0:.4f}".format(p1)))
                self.logger.info("0 Percentage: " + str("{0:.4f}".format(p0)))

                #if the 1s are over 95 percent of the total then pause
                if int(p1) > 95:
                    self.logger.info("Pausing")
                    self.paused = True
                    break

        self.logger.info("pin monitor Stopped #################")

    def start_gcode_failsafe(self, child_pipe):
        """
        Pausing and resuming print at start will execute gcode scripts in wrong order and drive the bed into the nozzle. Filament sensor should not pause print at start...
        Delete this function once a permanent fix has been adopted.
        """
        if self.pin_timer:
            self.logger.info("Five Minute Timer loop Started #################")
            timer_5m = self.timer(300)
            while not next(timer_5m) and not self.exit:
                self.exit_switch(child_pipe)
                continue
            self.logger.info("Five Minute Timer loop Stopped #################")

    def exit_switch(self, child):
        """checks pipe for exit switch"""
        poll = child.poll()
        if poll:
            data = child.recv()
            if 'exit' in data and data['exit']:
                self.exit = True
            else:
                self.exit = False

            if 'ack_alive' in data:
                self.logger.info("We are alive and kicking!")

    def timer(self, interval):
        """
        Timer that yields if interval has been met. Timer starts when generator instantiates.
        :param: int(seconds)
        :yields: boolean
        """
        last = datetime.now()
        while True:
            now = datetime.now()
            delta = now - last
            if delta.seconds >= interval:
                last = now
                yield True
            else:
                yield False

    def run_results(self, child):
        if self.paused:
            header = {'Content-Type': 'application/json', 'X-Api-Key': self.api_key}
            payload = {'command': 'pause','action': 'pause'}
            url = "http://127.0.0.1/api/job"
            self.logger.info("Requesting A pause from octoprint!")
            r = requests.post(url, headers=header, data=json.dumps(payload))
            self.logger.info(str(r))
            child.send(True)
        elif self.exit:
            self.logger.info("Process " + str(os.getpid()) +" Exiting" )
            sys.exit()
        else:
            self.logger.info("Process is exiting, but not due to a pause or exit.")
