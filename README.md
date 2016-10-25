Pause print on GPIO filament runout sensor

The following needs to be added to the config.yaml in the plugins section:

```
plugins:
  filament:
    pin: XX
	filament: 0
    bounce: 400	
	gcode_runout: "M0"
	gcode_loaded: ""
```

where XX represent the GPIO pin where your sensor is connected. Use `GPIO.BCM` notation. See [this](http://raspberrypi.stackexchange.com/questions/12966/what-is-the-difference-between-board-and-bcm-for-gpio-pin-numbering) good explation of GPIO.BOARD vs GPIO.BCM.

An API is available to check the filament sensor status via a GET method to `/plugin/filament/status` which returns a JSON

- `{status: "-1"}` if the sensor is not setup
- `{status: "0"}` if the sensor is OFF (filament not present)
- `{status: "1"}` if the sensor is ON (filament present)

The status 0/1 depends on the type of sensor. The setting `filament` determines the type of sensor (normaly open or normaly closed). Set to the value read from the GPIO when the **filament is present**.

`gcode_runout` is a comma separated list of gcode (ex: "M0, M300 @beep, M70 Replace the fillament") that will be sent to the printer when fillament runout. (GPIO value changes to the opposite of `filament` (raise or fall))

`gcode_loaded` is a comma separated list of gcode that will be sent to the printer when the filament is loaded. (GPIO value changes to the same values as `filament` (fall or raise))

An `Events.FILAMENT_RUNOUT` or `Events.FILAMENT_LOADED` would be triggered when the status changes and other plugins can action of it. See [documentation](http://docs.octoprint.org/en/devel/plugins/mixins.html#eventhandlerplugin) regarding the OctoPrint events. The FILAMENT events are injected at runtime and not mentioned in the original documentation.  

The setting `bounce` represent the sensitivity of your switch. The higher the number the less sensitive. Small numbers might give fake reads and cause **unwanted results**.

A build using an optical switch can be found at http://www.thingiverse.com/thing:1646220

Note: Needs RPi.GPIO version greater than 0.6.0 to allow access to GPIO for non root and `chmod a+rw /dev/gpiomem`.
This requires a fairly up to date system.


WARNING: I am **not responsible** for any failed prints. Use at your own risk. 