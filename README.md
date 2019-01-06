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
    "args":"--vol -2500 --live --timeout 30",
		"rtsp": "rtsp://192.168.1.30:7447/5c2e1fa0e4b07d23111c8161_1"
	}
}
```
