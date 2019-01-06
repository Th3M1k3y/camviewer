## Install instructions
# sudo apt-get install omxplayer screen

import os, urlparse, time, sys, urllib2, subprocess, datetime, json, argparse
import mqtt.client as mqtt

streams = {}
layout = {}
running = {}

include_modified_streams = 0.0
include_modified_layout = 0.0

parser = argparse.ArgumentParser(description='Start viewer')
parser.add_argument('--layout', help="Layout file to use", default="inc_layout_2x2.cfg")
parser.add_argument('--streams', help="Stream list file to use", default="inc_streams.cfg")
parser.add_argument('--mqttbroker', help="IP of the MQTT broker", default="")
commandArgs = parser.parse_args()

streamsrunning = False
mqtt_connected = False
basepath = os.path.dirname(os.path.realpath(__file__)) + "/"

player_env = os.environ.copy()

def logmsg(msg):
    print(msg)
    now = datetime.datetime.now()
    with open("/var/log/unifi_view.log", "a") as myfile:
        myfile.write(now.strftime("%Y-%m-%d %H:%M:%S") + " " + msg + "\n")
        myfile.close()

def json_load(jsonfile):
    output = {}
    f = open(jsonfile, 'r')
    content = f.read()
    f.close()
    try:
        return json.loads(content)
    except ValueError, e:
        logmsg(">>> JSON error in {file}".format(file=jsonfile))
        return {}

def init_streams():
    global include_modified_streams, streams
    logmsg("Reading streams from {basepath}{streams}".format(basepath=basepath, streams=commandArgs.streams))
    streams = json_load(basepath + commandArgs.streams)
    type(streams)
    include_modified_streams = os.stat(basepath + commandArgs.streams).st_mtime

def init_layout():
    global include_modified_layout, layout
    logmsg("Reading layout from {basepath}{layout}".format(basepath=basepath, layout=commandArgs.layout))
    layout = json_load(basepath + commandArgs.layout)
    type(layout)
    include_modified_layout = os.stat(basepath + commandArgs.layout).st_mtime

def measure_temp():
    temp = os.popen("vcgencmd measure_temp").readline()
    return (temp.replace("temp=",""))

def start_player(x1, y1, x2, y2, rtsp, id):
    if streams[id].has_key('args'):
        os.system("screen -dmS {id} sh -c 'omxplayer --avdict rtsp_transport:tcp --win \"{x1} {y1} {x2} {y2}\" {rtsp} {args} --dbus_name org.mpris.MediaPlayer2.omxplayer.{id}'".format(x1=x1, y1=y1, x2=x2, y2=y2, rtsp=rtsp, id=id, args=streams[id]['args']))
    else:
        os.system("screen -dmS {id} sh -c 'omxplayer --avdict rtsp_transport:tcp --win \"{x1} {y1} {x2} {y2}\" {rtsp} --live -n -1 --timeout 30 --dbus_name org.mpris.MediaPlayer2.omxplayer.{id}'".format(x1=x1, y1=y1, x2=x2, y2=y2, rtsp=rtsp, id=id))

def set_player_env():
    global player_env
    playerbus = open("/tmp/omxplayerdbus.root", 'r')
    player_env["DBUS_SESSION_BUS_ADDRESS"] = playerbus.read().strip()
    playerbus.close()
    
    playerpid = open("/tmp/omxplayerdbus.root.pid", 'r')
    player_env["DBUS_SESSION_BUS_PID"] = playerpid.read().strip()
    playerpid.close()
        
def check_player(player_id, player_rtsp):
    test = subprocess.Popen(['dbus-send', '--print-reply=literal', '--session', '--reply-timeout=1000', '--dest=org.mpris.MediaPlayer2.omxplayer.' + str(player_id), '/org/mpris/MediaPlayer2', 'org.freedesktop.DBus.Properties.Position'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=player_env)
    stdout,stderr = test.communicate()
    position = stdout.strip()
    
    position = position.split(" ")
       
    if position[0] == "int64" and int(position[1]) > 0:
        return True # player is fine
    else:
        logmsg("{id}: {stdout} - Error: {stderr}".format(id=player_id, stdout=stdout.strip(), stderr=str(stderr)))
        player_pid = get_player_pid(player_rtsp)
        screen_pid = get_screen_pid(player_rtsp)
        if player_pid != -1:
            logmsg("Trying to fix " + player_id)
            os.system("kill -9 " + str(player_pid))
            os.system("kill -9 " + str(screen_pid))
        else:
            logmsg("Could not determine PID for " + player_id)
            os.system("killall omxplayer screen")
            
    return False # something is wrong with the player
    
def get_player_pid(stream):
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    for pid in pids:
        try:
            out = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read().split('\0')
            if 'omxplayer' in out[0]:
                if out[5].strip() == stream.strip():
                    return int(pid)
        except IOError: # proc has already terminated
            return -1
            
def get_screen_pid(stream):
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    for pid in pids:
        try:
            out = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read().split('\0')
            if 'SCREEN' in out[0]:
                if stream in out[5]:
                    return int(pid)
        except IOError: # proc has already terminated
            return -1

def startstrim():
    global streamsrunning
    init_streams()
    init_layout()
    streamsrunning = True
    os.system("killall omxplayer.bin") # Make sure there is no leftover streams running
    logmsg("Starting streams")
    for pos in layout:
        if pos in streams: # Check if the layout position has been found in the list of streams
            running[pos] = streams[pos]['rtsp']
            logmsg("Starting {rtsp} on {pos}".format(rtsp=running[pos], pos=pos))
            start_player(layout[pos]['x1'], layout[pos]['y1'], layout[pos]['x2'], layout[pos]['y2'], streams[pos]['rtsp'], pos)

def stopstrim():
    global streamsrunning
    streamsrunning = False
    time.sleep(1)
    logmsg("Killing omxplayer")
    os.system("killall omxplayer")
    os.system("killall screen")
       
def on_message(client, userdata, message):
    msg = str(message.payload.decode("utf-8"))
    if message.topic == "/unifi/video/monitor":
        if msg == "1":
            logmsg("MQTT: Received ON message")
            os.system("vcgencmd display_power 1")
            startstrim()
        elif msg == "0":
            logmsg("MQTT: Received OFF message")
            stopstrim()
            time.sleep(2)
            os.system("vcgencmd display_power 0")
    elif message.topic == "/unifi/video/monitor/cmd":
        if msg == "10":
            logmsg("MQTT: Received REPAIR message")
            stopstrim()
            time.sleep(2)
            startstrim()
        elif msg == "20":
            logmsg("MQTT: Received RESTART message")
            os.system("reboot")

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    logmsg("MQTT: Disconnected")
    while mqtt_connected == False:
        time.sleep(15)
        logmsg("MQTT: Reconnecting")
        client.reconnect()
        
def on_connect(client, userdata, flags, rc):
    logmsg("Connection returned result: " + connack_string(rc))
    global mqtt_connected
    mqtt_connected = True

def main():
    logmsg(">> Starting")
    
    with open('/boot/config.txt', 'r') as f:
        found = False
        for line in f:
            cmd = line.strip().split('=')
            if cmd[0] == "gpu_mem":
                found = True
                if int(cmd[1]) < 256:
                    found = False
        if found == False:
            print("Consider using at least 256MB for gpu memory by adding 'gpu_mem=256' to /boot/config.txt")
            time.sleep(15) # Allow some time for the message to be seen
    
    if len(commandArgs.mqttbroker) > 7:
        logmsg("MQTT: Setting up")
        client = mqtt.Client("UniFi Video Monitor")
        client.on_message=on_message
        client.on_disconnect=on_disconnect
        client.connect(commandArgs.mqttbroker)
        client.loop_start() #start the loop
        client.subscribe("/unifi/video/monitor")
        client.subscribe("/unifi/video/monitor/cmd")
        client.publish("/unifi/video/sync/state","ON")
    else:
        logmsg("MQTT not in use, starting streams")
        startstrim()
    
    logmsg("Killing all screens and omxplayers")
    os.system("killall omxplayer screen")
    logmsg("Watchdoge started")
    while True:
        if streamsrunning == True:
            time.sleep(30)
        else:
            time.sleep(60)
        
        if streamsrunning == True:
            if os.stat(basepath + commandArgs.layout).st_mtime != include_modified_layout or os.stat(basepath + commandArgs.streams).st_mtime != include_modified_streams:
                logmsg("Reloading streams and layout")
                stopstrim()
                time.sleep(1)
                init_streams()
                init_layout()
                startstrim()
            else:
                os.system('clear')
                set_player_env() # Set player environment
                for pos in running:
                    if check_player(pos, running[pos][1]) is False:
                        logmsg("{pos} is not playing {rtsp}".format(rtsp=running[pos], pos=pos))
                        start_player(layout[pos]['x1'], layout[pos]['y1'], layout[pos]['x2'], layout[pos]['y2'], streams[pos]['rtsp'], pos)
        else:
            os.system("killall omxplayer screen")
    logmsg("Watchdoge stopped")
            
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            print("Killing everything")
            stopstrim()
            client.loop_stop() #stop the loop
            sys.exit(0)
        except SystemExit:
            os._exit(0)