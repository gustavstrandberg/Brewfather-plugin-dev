import json
import time
import paho.mqtt.client as mqtt
from eventlet import Queue
from modules import cbpi, app, ActorBase
#import requests

q =  Queue

@cbpi.backgroundtask(key='mqtt_listener', interval=1)
def mqtt_listener_background_task(self):

    def on_message(client, userdata, msg):
        topic=msg.topic
        msg_decode=str(msg.payload.decode("utf-8","ignore"))
        print("MQTT data Received",msg_decode)
        msg_in=json.loads(msg_decode)
   
        if "pump" in msg_in:
            if msg_in["pump"] == "on":
                #r = requests.post("http://localhost:5000/api/actor/2/switch/on")
                #print r.status_code
                print("Starting Pump, pump = ",msg_in["pump"])
                self.switch_actor_on(2) 
                #self.api.app.logger.info("PUMP ON")
            if msg_in["pump"] == "off":
                #requests.post('http://localhost:5000/api/actor/2/switch/off')
                print("Stopping Pump, pump = ",msg_in["pump"])
                self.switch_actor_off(2)
        elif "start" in msg_in:
            if msg_in["start"] == "auto":
                print("Starting Brew, start = ",msg_in["start"])
            if msg_in["start"] == "off":
                print("Stopping Brew, start = ",msg_in["start"])
    
    def on_connect(client, userdata, flags, rc):
           print("Connected With Result Code " (rc))

    def on_disconnect(client, userdata, rc):
           print("Client Got Disconnected")

    topic="cbpi/homebrewing/uuid/commands"
    client=mqtt.Client("cbpi_mqtt_listener_test")
 #   client.on_connect=on_connect
 #   client.on_disconnect=on_disconnect
    client.on_message=on_message
    client.connect("localhost") 
    client.loop_start()
    client.subscribe(topic)
#    client.publish(topic,"test")
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    pass
