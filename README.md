Pause print on GPIO filament runout sensor

The following need to be added to the config.yaml:

```
plugins:
  filament:
    pin: XX
    bounce: 400
```
where XX represent the GPIO pin where your sensor is connected.

An API is available to check the filament sensor status via a GET method to `/plugin/filament/status` which returns a JSON

- `{status: "-1"}` if the sensor is not setup
- `{status: "0"}` if the sensor is OFF (filament not present)
- `{status: "1"}` if the sensor is ON (filament present)

The status 0/1 depends on the type of sensor, and it might be reverse if using a normaly closed switch.

A build using an optical switch can be found at http://www.thingiverse.com/thing:1646220

Note: Needs RPi.GPIO version greater than 0.6.0 to allow access to GPIO for non root and `chmod a+rw /dev/gpiomem`.
This requires a fairly up to date system.

WARNING: I am **not responsible** for any failed prints. Use at your own risk.

# ChangeLog

### 2.6
- Filament sensor no longer uses multiple processes. Only one process active the entire time.
- Communication improved between parent and child process
- Child process will die when parent process is no longer alive
- Filament sensor will respond to error events now