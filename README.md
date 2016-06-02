Pause print on GPIO sensor

add settings to config.yaml

```
  octoprint_filament:
    pin: 30
    bounce: 400
```


Needs RPi.GPIO version greater than 0.6.0 to allow access to GPIO for non root and chmod a+rw /dev/gpiomem