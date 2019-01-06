# Intro
This script is made for viewing streams from surveillance cameras. It has been tested with streams from MotionEye, an Onvif compatible camera, and rtsp streams from UniFi Video.

To be able to detect stalled streams, and restart them, this script must be run as root.

The start of this little project, was [this thread](https://community.ubnt.com/t5/UniFi-Video/Tutorial-Raspberry-Pi-3-RTSP-Stream-Viewer/m-p/1536448) on the Ubnt forum, and inspired by [this repository](https://github.com/Anonymousdog/displaycameras), which can also cycle through the streams, check it out if you need such functions.

## Dependencies
This is developed and tested on a Raspberry Pi 3b+, and this is what this documentation is expecting to be used.

Before starting, make sure your system is up to date, then use `sudo apt-get install omxplayer screen` to install omxplayer and screen, which is both needed for this script to function.

# Configuration
## Layouts
Multiple layouts can be stored, and selected with the --layout argument, as default `inc_layout_2x2.cfg` will be used.

Layouts are stored in json format, "c1", "c2", and so on, can be named whatever. `view.py` will read both the layout and streams file, then go through the layout, and search the streams for the same name, to figure out which stream should be assigned to which frame.
### 2x2 Example
```json
{
	"c1": {
		"x1": 0,
		"y1": 0,
		"x2": 958,
		"y2": 538
	},
	"c2": {
		"x1": 960,
		"y1": 0,
		"x2": 1919,
		"y2": 538
	},
	"c3": {
		"x1": 0,
		"y1": 540,
		"x2": 958,
		"y2": 1079
	},
	"c4": {
		"x1": 960,
		"y1": 540,
		"x2": 1919,
		"y2": 1079
	}
}
```

## Streams
The streams is defined in json format, like the layout. "c1", "c2", and so on, can be changed like in the layout file, but must match a field in the layout, to be assigned to it.

In this example, c4 is assigned to a rtsp stream with audio, to get the audio from that stream, `args` has been defined, which will remove the standard arguments needed for omxplayer to play the video streams, and instead these custom arguments will be inserted.
Notice, on a raspberry pi, only one audio source can be active.
### Example
```json
{
	"c1": {
		"name": "Garage 1",
		"rtsp": "http://192.168.1.30:8084"
	},
	"c2": {
		"name": "Garage 2",
		"rtsp": "http://192.168.1.30:8081"
	},
	"c3": {
		"name": "Living room",
		"rtsp": "http://192.168.1.30:8082"
	},
	"c4": {
		"name": "Front door",
		"args": "--vol -2500 --live --timeout 30",
		"rtsp": "rtsp://192.168.1.30:7447/5c2e1fa0e4b07d23111c8161_1"
	}
}
```
## MQTT
MQTT can be used to turn the monitor on and off.
Enable MQTT with the argument `--mqttbroker` and it will then subscribe to topic `/unifi/video/monitor` and `/unifi/video/monitor/cmd`.
Receiving `1`on `/unifi/video/monitor` will turn hdmi output on and start the streams, while receiving `0` will kill all omxplayer and screen processes running and turn the hdmi output off.

On `/unifi/video/monitor/cmd` a `10`command can be send, which will stop all players and start them again, or `20` which will reboot the Raspberry Pi.

While starting the script, an `ON` message will be send on `/unifi/video/sync/state`, which can be used to trigger a rule in the system handling the MQTT messages.

### OpenHAB example
#### Items
```
Switch	unifi_monitor		"Monitor [%s]"	<screen> (startRestore)	{mqtt=">[broker:/unifi/video/monitor:command:ON:1],>[broker:/unifi/video/monitor:command:OFF:0],<[broker:/unifi/video/monitor/state:state:default]"}
Switch	unifi_video_sync						{mqtt="<[broker:/unifi/video/sync/state:state:default]"}
String  unifi_monitor_cmd 	"Commands"	<camera>		{mqtt=">[broker:/unifi/video/monitor/cmd:command:10:10],>[broker:/unifi/video/monitor/cmd:command:20:20]", autoupdate="false"}
```

#### Rule
```
rule "Sync unifi modules"
when
	Item unifi_video_sync received update
then
	var String itemState = unifi_monitor.state.toString()
	sendCommand(unifi_monitor, itemState)
end
```

#### Sitemap
```
sitemap thesite label="My site"
{
	Frame label="UniFi"
	{
		Switch item=unifi_monitor
		Switch item=unifi_monitor_cmd mappings=[10="Repair",20="Reboot"]
	}
}
```

## Start on boot
There are multiple ways of making the script start on boot, this is the way I decided to do it.
`sudo nano /etc/rc.local` then insert `python /home/pi/unifi/view.py` just before `exit 0`.

If you want to activate MQTT, it could be done with `python /home/pi/unifi/view.py --mqttbroker "192.168.1.30"`
