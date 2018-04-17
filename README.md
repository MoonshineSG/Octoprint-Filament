### see the improved version at https://github.com/kontakt/Octoprint-Filament-Reloaded

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

=== How to install ===

For some older Octopi installs, the plugin won't work before you make sure you have everything set up to date. Here are the steps to ensure you have everyting in place for the plugin. 

 0- you can check your system version with 
- `uname -a` 
Version below 0.4.xx are not known to work well. 

 1- Upgrade your Octopi system (Raspian Linux tailored to Octoprint) :
 Login via SSH. Default admin user is pi
 - `ssh -l pi  octopi.local`  
 
 Update the list of package and then upgrade your system. It will upgrade RPi.GPIO and gives you a /dev/gpiomem device. Both are needed Reboot.
  - `sudo apt-get update`
  - `sudo apt-get upgrade`
  - `reboot` 
  
  Then you can check your system version again with 
  - `uname -a` 

 2- Edit the Octoprint config file manually 
 
 - `nano ~/.octoprint/config.yaml`
 go down to the plugins section using arrows, and insert the filament settings
 
 inside the
 ```
plugins:
```
section,  

insert this respecting the spaces:
 ```
  filament:
    pin: XX
    bounce: 400
```
Where XX is the GPIO number on your Raspberry Pi where you plug the signal (S) pin fo your sensor. We suggest using GPIO 17. You can take a look at the pinout map here: http://pinout.xyz

Save by typing ctrl-X and then Y (for yes)

 3- Give access to non-root user to the GPIO device
 
  - `sudo chmod a+rw /dev/gpiomem`
 
 4- install the plugin using the plugin manager in the Octoprint web interface

http://octopi.local/#settings_plugin_pluginmanager

click Get More button, and search for Filament.

This plugin is Filament. Filament-Reloaded is a fork. This guide is for Filament, not Filament-Reloaded.

Install and then follow the instructions to restart Octoprint.

 5- Once Octoprint is restarted, test your sensor using the web get API.
 
 Simply type the URL in your browser :
 
 http://octopi.local/plugin/filament/status?apikey=xxxxxxxxxxx
 
 Where octopi.local is the local domain or IP of your octoprint server and the API key is the one found in http://octopi.local/#settings_api
 
 It should return 
 - `{status: "-1"}` if the sensor is not setup
- `{status: "0"}` if the sensor is OFF (filament not present)
- `{status: "1"}` if the sensor is ON (filament present)



### Donate

Accepting [beer tips](https://paypal.me/ovidiuhossu)...
