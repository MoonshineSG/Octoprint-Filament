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
import traceback

class pinMonitor():
    def __init__(self, printer_api, switch_pin, **kwargs):
        self.switch_pin = switch_pin
        self.api_key = printer_api
        self.paused = False
        self.counter1 = 0
        self.counter0 = 0
        self.lock_1_timer = False
        self.monitor = None
        logging.basicConfig(filename='/home/pi/.octoprint/logs/octoprint.log', level=logging.INFO)
        self.logger = logging
        self.logger.info("Pin Monitor made with api key: " + str(self.api_key))
        self.start_monitor()

    def start_monitor(self):
        self.parent_pid = os.getpid()
        self.parent_pipe, self.child_pipe = multiprocessing.Pipe()
        self.monitor = multiprocessing.Process(target=self.run_monitor, args=(self.child_pipe,))
        
        self.logger.info("Starting monitor! ########################")
        self.monitor.start()

        self.logger.info("Process " + str(self.monitor.pid) +" is assigned to the pin monitor." )

        

    def monitor_pipe(self):
        poll = self.parent_pipe.poll()
        if poll:
            data = self.parent_pipe.recv()
            if data:
                return data

        return False

    #filament options
    '''
    MONITOR_ON - resume monitoring 
    MONITOR_PAUSE - pause monitoring
    MONITOR_OFF - stop monitoring and go into hibernation
    TIMER_SET - set timer to true
    TIMER_OFF - force timer to false
    RESET_PAUSE_FLAG - reset self.paused to False
    '''

    def get_event(self):
        data = None
        if self.child_pipe.poll():
            data = self.child_pipe.recv()
        # if data != None:
        #     self.logger.info(str(data))
        return data


    def run_monitor(self, child_pipe):
        try:
            self.logger.info("Process " + str(os.getpid()) +" Starting for Pin Monitor" )
            self.child_pipe = child_pipe

            self.logger.info("Initializing Pin")
            self.initialize_pin()

            #monitor the state of the machine and the state of the parent process. If it dies so should we
            last_action = None
            parent_alive = True
            while parent_alive:
                parent_alive = self.check_pid(self.parent_pid)
                action = self.get_event()

                available_actions = {
                    'MONITOR_ON': self.monitor_on,
                    'MONITOR_PAUSE': self.monitor_pause,
                    'MONITOR_OFF': self.monitor_off,
                    'TIMER_SET': self.timer_set,
                    'TIMER_OFF': self.timer_off,
                    'RESET_PAUSE_FLAG': self.reset_paused,

                }


                if action != None and 'action' in action and action['action'] in available_actions:

                    #should we log the action?
                    if 'ack_command' in action and action['ack_command']:
                        available_actions[action['action']](verbose=True)        
                    else:
                        available_actions[action['action']]()

                    last_action = action['action']
                
                elif last_action != None:
                    #if we have paused there is no need to monitor the pin anymore. Waiting for a pause command to turn off monitoring will fill the logs with nonsense
                    if self.paused and last_action == 'MONITOR_ON':
                        last_action = 'MONITOR_PAUSE'
                    available_actions[last_action]()

                else:
                    #if no condition is set and no commands available, then just be off
                    available_actions['MONITOR_OFF']()

            if not parent_alive:
                self.logger.info("Parent process is no longer alive. Exiting")

        except Exception as e:
            self.logger.info("ERROR!!!!!!!!!!!!!!!!!!!!!!! " + str(e))
            traceback.print_exc()

    def reset_paused(self, verbose = False):
        if verbose:
            self.logger.info("Resetting self.paused to False")
        self.paused = False

    def monitor_off(self, verbose=False):
        #don't process anything and sleep
        if verbose:
            self.logger.info("Sleeping for Five Seconds!")
        time.sleep(5)

    def monitor_pause(self, verbose=False):
        #Be a busy waiter
        if verbose:
            self.logger.info("Sleeping for 0.2 Seconds!")
        time.sleep(0.2)

    def monitor_on(self, verbose=False):
        #either start the monitor or start the monitor after five minutes
        if not self.timer:
            if verbose:
                self.logger.info("Starting Pin Monitor without a timer")
            self.monitor_pin()
        elif self.timer and self.timer_done():
            if verbose:
                self.logger.info("Starting Pin Monitor with a timer")
            self.monitor_pin()
        else:
            if verbose:
                self.logger.info("Waiting for timer")
            return

        #pause if we need to pause.
        self.run_results()

    def timer_set(self, verbose=False):
        if verbose:
            self.logger.info("Setting 5 minute timer!")
        self.end_time = time.time() + 300
        self.timer = True

    def timer_done(self):
        delta_time = self.end_time - time.time()
        if delta_time > 0:
            return False
        else:
            self.timer = False #avoid this function for mildly faster monitor pin activation
            return True

    def timer_off(self, verbose=False):
        if verbose:
            self.logger.info("Turning off timer!")
        self.timer = False        

    def check_pid(self, pid):        
        """ Check For the existence of a pid. """
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True


    def initialize_pin(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.switch_pin, GPIO.IN, GPIO.PUD_UP)

    def monitor_pin(self):
        #check the state of the pin
        self.counter0 = 0
        self.counter1 = 0
        pin_state = GPIO.input(self.switch_pin)
        if pin_state == 1:
            #set timer
            timer_15s = self.seconds_timer(15)
            self.counter0 = 0
            self.counter1 = 0
            while not next(timer_15s):
                pin_state = GPIO.input(self.switch_pin)
                if pin_state == 1:
                    self.counter1 += 1
                elif pin_state == 0:
                    self.counter0 += 1
            # Calculate confidence interval
            total = self.counter0 + self.counter1
            
            p1 = 0
            p0 = 0
            if self.counter1 >= 1:
                p1 = float((float(self.counter1) / float(total)) * 100.00)
                p0 = float((float(self.counter0) / float(total)) * 100.00)

            #if the 1s are over 95 percent of the total then pause
            if int(p1) > 95:
                #only log if theres a pause needed. Otherwise the log will be filled with misfires
                self.logger.info("Total: " + str(total) + " 1s: " + str(self.counter1) + " 0s: " + str(self.counter0))
                self.logger.info("1 Percentage: " + str("{0:.4f}".format(p1)))
                self.logger.info("0 Percentage: " + str("{0:.4f}".format(p0)))

                self.logger.info("Pausing")
                self.paused = True

    def seconds_timer(self, interval):
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

    def run_results(self):
        if self.paused:
            header = {'Content-Type': 'application/json', 'X-Api-Key': str(self.api_key)}
            payload = {'command': 'pause','action': 'pause'}
            url = "http://127.0.0.1/api/job"
            self.logger.info("Requesting A pause from octoprint!")
            r = requests.post(url, headers=header, data=json.dumps(payload))
            if r.status_code == 200 or r.status_code == 204:
                self.child_pipe.send(True)
            else:
                self.logger.info(str(r))