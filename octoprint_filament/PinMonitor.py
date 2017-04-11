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

    def stop_monitor(self):
        self.logger.info("Stopping monitor! ########################")
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
        self.start_gcode_failsafe()
        self.monitor_pin(child_pipe)
        self.run_results(child_pipe)

    def initialize_pin(self):
        self.logger.info("Process " + str(os.getpid()) +" Starting for Pin Monitor" )
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.switch_pin, GPIO.IN, GPIO.PUD_UP)

    def monitor_pin(self, child):
        self.logger.info("Pin Monitor Started #################")
        while not self.paused and not self.exit:
            self.exit_switch()
            if self.exit: continue
            #check the state of the pin
            self.counter0 = 0
            self.counter1 = 0
            state = GPIO.input(self.switch_pin)
            if state ==1:
                #set timer
                timer_15s = self.timer(15)
                self.counter0 = 0
                self.counter1 = 0
                while next(timer_15s) and not self.exit:
                    self.exit_switch()
                    if self.exit: break
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

    def start_gcode_failsafe(self):
        """
        Pausing and resuming print at start will execute gcode scripts in wrong order and drive the bed into the nozzle. Filament sensor should not pause print at start...
        Delete this function once a permanent fix has been adopted.
        """
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

    def exit_switch(self):
        """checks pipe for exit switch"""
        poll = child.poll()
        if poll:
            data = child.recv()
            self.exit = data.get('exit', False)

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

            r = requests.post(url, headers=header, data=json.dumps(payload))
            #self.logger.info(r.text)
            child.send(True)
        elif self.exit:
            self.logger.info("Process " + str(os.getpid()) +" Exiting" )
            sys.exit()
