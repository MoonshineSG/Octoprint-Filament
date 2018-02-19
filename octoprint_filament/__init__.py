# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.settings
import octoprint.util

from octoprint.events import eventManager, Events
from flask import jsonify, request

import logging
import logging.handlers
import RPi.GPIO as GPIO 
from .PinMonitor import pinMonitor

class FilamentSensorPlugin(octoprint.plugin.StartupPlugin,
                           octoprint.plugin.ShutdownPlugin,
                            octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.EventHandlerPlugin,
                            octoprint.plugin.BlueprintPlugin):

    def __init__(self):
        super(FilamentSensorPlugin, self).__init__()
        self.pin_monitor = None


    def initialize(self):
        self._logger.setLevel(logging.DEBUG)
        
        self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
        if GPIO.VERSION < "0.6":
            raise Exception("RPi.GPIO must be greater than 0.6")
            
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        self.we_paused = False
        
        self._logger.info("Filament Sensor Plugin [%s] initialized..."%self._identifier)

    def on_after_startup(self):
        self.PIN_FILAMENT = self._settings.get(["pin"])
        self.BOUNCE = self._settings.get_int(["bounce"])
        
        if self.PIN_FILAMENT != -1:
            self._logger.info("Filament Sensor Plugin setup on GPIO [%s]...###################"%self.PIN_FILAMENT)
            
            api_key = self._settings.global_get(['api', 'key'])
            self._logger.info(api_key)
            self.pin_monitor = pinMonitor(api_key, self.PIN_FILAMENT)
        
    def get_settings_defaults(self):
        return dict(
            pin = -1,
            bounce = 300
        )

    def start_monitoring(self, timer=False, **kwargs):
        api_key = self._settings.global_get(['api', 'key'])
        
        
    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            self.send_monitor_info('RESET_PAUSE_FLAG', ack_command=True)
            self.send_monitor_info('TIMER_SET', ack_command=True)
            self.send_monitor_info('MONITOR_ON', ack_command=True)
            self._logger.info("Print Started")

        elif event in [Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED, Events.ERROR, Events.DISCONNECTED]:
            self._logger.info("Print Stopped")
            self.send_monitor_info('RESET_PAUSE_FLAG', ack_command=True)
            self.send_monitor_info('MONITOR_OFF', ack_command=True)

        elif event == Events.PRINT_PAUSED:
            self.send_monitor_info('MONITOR_PAUSE', ack_command=True)

        elif event == Events.PRINT_RESUMED:
            self.we_paused = False
            self.send_monitor_info('RESET_PAUSE_FLAG', ack_command=True)
            self.send_monitor_info('TIMER_OFF', ack_command=True)
            self.send_monitor_info('MONITOR_ON', ack_command=True)
            self._logger.info("Print Resumed!")

    #filament options
    '''
    MONITOR_ON - resume monitoring 
    MONITOR_PAUSE - pause monitoring
    MONITOR_OFF - stop monitoring and go into hibernation
    TIMER_SET - set timer to true
    TIMER_OFF - force timer to false
    RESET_PAUSE_FLAG - reset the pause flag
    '''
    def send_monitor_info(self, command, ack_command = False):
        if self.pin_monitor != None:
            available_commands = ['MONITOR_ON', 'MONITOR_PAUSE', 'MONITOR_OFF', 'TIMER_SET', 'TIMER_OFF', 'RESET_PAUSE_FLAG']
            if command in available_commands:
                command_package = {
                    'action': command,
                    'ack_command': ack_command
                }
                self.pin_monitor.parent_pipe.send(command_package)
        
    def check_filament_pause(self):
        if hasattr(self, 'pin_monitor') and self.pin_monitor != None:
            for x in range (0, 10):
                data = self.pin_monitor.monitor_pipe()
                #self._logger.info("Pipe Data: " + str(data))
                if data:
                    return data
        else:
            return False

    def get_version(self):
        return self._plugin_version

    def get_update_information(self):
        return dict(
            octoprint_filament=dict(
                displayName="Filament Sensor",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="Robo3D",
                repo="OctoPrint-Filament",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/Robo3D/OctoPrint-Filament/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "Filament Sensor"
__plugin_version__ = "2.0"
__plugin_description__ = "Use a filament sensor to pause printing when filament runs out."

def __plugin_load__():
    global __plugin_implementation__
    global __plugin_helpers__
    __plugin_implementation__ = FilamentSensorPlugin()
    __plugin_helpers__ = dict(check_auto_pause=__plugin_implementation__.check_filament_pause)

