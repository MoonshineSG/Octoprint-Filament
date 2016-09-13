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

class FilamentSensorPlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.EventHandlerPlugin,
							octoprint.plugin.BlueprintPlugin):

	CLOSED = 1
	OPEN = 0
	
	def initialize(self):
		self._logger.setLevel(logging.DEBUG)
		
		self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		if GPIO.VERSION < "0.6":
			raise Exception("RPi.GPIO must be greater than 0.6")
			
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		
		self._logger.info("Filament Sensor Plugin [%s] initialized..."%self._identifier)

	def on_after_startup(self):
		self.PIN_FILAMENT = self._settings.get(["pin"])
		self.BOUNCE = self._settings.get_int(["bounce"])
		self.FILAMENT = self._settings.get(["filament"])
		
		if self.FILAMENT not in [self.CLOSED, self.OPEN]:
			raise Exception("Invalid value for switch type.")

		if self.PIN_FILAMENT != -1:
			GPIO.setup(self.PIN_FILAMENT, GPIO.IN)
			self._logger.info("Filament Sensor Plugin setup indicates '%s' when filament is present (setup on GPIO %s)."%(self.FILAMENT, self.PIN_FILAMENT))
			self._logger.info("Current status is '%s'..."%GPIO.input(self.PIN_FILAMENT))
			#self.setup_detection()
		else:
			self._logger.error("Filament Sensor Plugin not fully setup. Check your settings. [PIN_FILAMENT = -1]")
			
			
	def get_settings_defaults(self):
		return dict(
			pin = -1,
			bounce = 300,
			filament = self.OPEN
		)

	@octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
	def check_status(self):
		status = -1
		if self.PIN_FILAMENT != -1:
				status = int(self.FILAMENT == self.CLOSED) if GPIO.input(self.PIN_FILAMENT) else int(self.FILAMENT != self.CLOSED)
		return jsonify( status = status )
		
	def on_event(self, event, payload):
		if event == Events.PRINT_STARTED:
			self._logger.info("Printing started. Filament sensor enabled.")
			self.setup_detection()
		elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
			self._logger.info("Printing stopped. Filament sensor disabled.")
			try:
				GPIO.remove_event_detect(self.PIN_FILAMENT)
			except:
				pass

	def setup_detection(self):
		try:
			GPIO.remove_event_detect(self.PIN_FILAMENT)
		except:
			pass
		if self.PIN_FILAMENT != -1:
			if self.FILAMENT == self.OPEN:
				self._logger.debug("Filament sensor setup for 'RISING' detection...")
				DIRECTION = GPIO.RISING
			else:
				self._logger.debug("Filament sensor setup for 'FALLING' detection...")
				DIRECTION = GPIO.FALLING

			GPIO.add_event_detect(self.PIN_FILAMENT, DIRECTION, callback=self.check_gpio, bouncetime=self.BOUNCE) 

	def check_gpio(self, channel):
		read = GPIO.input(self.PIN_FILAMENT)
		state = int(self.FILAMENT == self.CLOSED) ^ read
		self._logger.debug("Event on sensor. Runout ? [%s] (actual reading :[%s])."%(state, read))
		if state: #safety pin
			self._logger.info("Filament runout. Pause printing.")
			if self._printer.is_printing():
				self._printer.toggle_pause_print()

	def get_version(self):
		return self._plugin_version

	def get_update_information(self):
		return dict(
			octoprint_filament=dict(
				displayName="Filament Sensor",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="MoonshineSG",
				repo="OctoPrint-Filament",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/MoonshineSG/OctoPrint-Filament/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "Filament Sensor"
__plugin_version__ = "1.0.1"
__plugin_description__ = "Use a filament sensor to pause printing when filament runs out."

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = FilamentSensorPlugin()

