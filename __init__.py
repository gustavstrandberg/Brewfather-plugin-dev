# -*- coding: utf-8 -*-
import paho.mqtt.client as mqtt
from eventlet import Queue
from modules import cbpi, app, ActorBase

#gs
from modules.core.hardware import SensorActive, ActorBase
from modules.core.props import Property
from modules.steps import StepView
from modules.kettle import Kettle2View
import json
import os, re, threading, time
import requests

q = Queue()

def on_connect(client, userdata, flags, rc):
    print("BF MQTT Connected" + str(rc))

class BFMQTTThread (threading.Thread):

    def __init__(self,server,port,username,password,tls,deviceid):
        threading.Thread.__init__(self)
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.tls = tls
        self.deviceid = deviceid

    client = None
    def run(self):
        self.client = mqtt.Client(self.deviceid)
        self.client.on_connect = on_connect

        if self.username != "username" and self.password != "password":
            self.client.username_pw_set(self.username, self.password)
        
        if self.tls.lower() == 'true':
            self.client.tls_set_context(context=None)

        self.client.connect(str(self.server), int(self.port), 60)
        self.client.loop_forever()

@cbpi.actor
class BFMQTTControlObject(ActorBase):
    topic = Property.Text("Topic", configurable=True, default_value="cbpi/homebrewing/uuid/commands", description="MQTT TOPIC")
    object = Property.Text("Object", configurable=True, default_value="", description="Data Object, e.g. pump")
    def on(self, power=100):
        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({self.object: "on"}), qos=2, retain=True)

    def off(self):
        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({self.object: "off"}), qos=2, retain=True)

@cbpi.actor
class BFMQTTActorInt(ActorBase):
    topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
    def on(self, power=100):
        self.api.cache["mqtt"].client.publish(self.topic, payload=1, qos=2, retain=True)

    def off(self):
        self.api.cache["mqtt"].client.publish(self.topic, payload=0, qos=2, retain=True)

@cbpi.sensor
class BFMQTTListenerCommands(SensorActive):
    
    deviceid = 'c87052414df980'
    #deviceid = Property.Text("Device ID", configurable=True, description="Device ID from Brewfather Devices configiuration.") 
    #a_topic = 'cbpi/homebrewing/' + str(deviceid) + '/commands'
    a_topic = Property.Text("Topic", configurable=True, default_value='cbpi/homebrewing/' + str(deviceid) + '/commands', description="Brewfather MQTT TOPIC") 
    print "####################### a_topic = "
    print a_topic
    #a_topic = Property.Text("Topic", configurable=True, default_value="cbpi/homebrewing/deviceid/commands", description="Brewfather MQTT TOPIC")
    #a_topic = "cbpi/homebrewing/uuid/commands"
    #b_payload = Property.Text("Object payload", configurable=True, default_value="", description="Object in patload, e.g. pump, leave blank for raw payload")
    #b_payload = "pump"
    base_pump = Property.Actor(label="Pump Actor", description="Select the Pump actor you would like to control from Brewfather.")
    base_kettle = Property.Kettle(label="Kettle to control", description="Select the Kettle you would like to control from Brewfather.")
    #deviceid = Property.Text("Device ID", configurable=True, description="Device ID from Brewfather Devices configiuration.")
    
    last_value = None

    def init(self):
        self.topic = self.a_topic
        SensorActive.init(self)
        
        def on_message(client, userdata, msg):

            try:
                msg_decode=str(msg.payload.decode("utf-8","ignore"))
                print "" 
                print "==== START ====" 
                print("BF MQTT data Received",msg_decode)
                msg_in=json.loads(msg_decode)
                print "msg_in = "
                print msg_in
                print "==== SLUT ====" 

                if "pump" in msg_in:
                    if msg_in["pump"] == "on":
                        requests.post("http://localhost:5000/api/actor/" + self.base_pump + "/switch/on")
                        print("Starting Pump")
                        #self.api.switch_actor_on(2)
                    if msg_in["pump"] == "off":
                        requests.post("http://localhost:5000/api/actor/" + self.base_pump + "/switch/off")
                        print("Stopping Pump")
                        #self.api.switch_actor_off(2)

                if "start" in msg_in:
                    if msg_in["start"] == "auto":
                        requests.post("http://localhost:5000/api/kettle/" + self.base_kettle + "/automatic") 
                        print("Set kettle to automatic start") 
                
                if "recipe" in msg_in:
                    if msg_in["recipe"] == 1:
                        requests.post("http://localhost:5000/api/step/start")
                        print("Step start")

                if "stop" in msg_in:
                    if msg_in["stop"] == "true":
                        requests.post("http://localhost:5000/api/step/reset")
                        requests.post("http://localhost:5000/api/kettle/" + self.base_kettle + "/automatic")
                        requests.post("http://localhost:5000/api/actor/" + self.base_pump + "/switch/off")
                        print("Stopping step")
                #elif "stop" in msg_in:
                #    if msg_in["stop]" == "auto":
                #        print("St Brew, start = ",msg_in["start"])
                #    if msg_in["stop"] == "true":
                #        print("Stopping Brew, start = ",msg_in["start"])

            except Exception as e:
                print e
        
        #on_message.sensorid = self.id
        self.api.cache["mqtt"].client.subscribe(self.topic)
        self.api.cache["mqtt"].client.message_callback_add(self.topic, on_message)


#    def get_value(self):
#        # Control base actor from MQTT.
#        print "=== get_value ==="
#        print "self.last_value = "
#        print self.last_value 
#        print "msg_in ="
#        #print msg_in
        
#        if (self.last_value == "off") :
#                self.api.switch_actor_off(int(self.base_pump))
#                print "Pump2 OFF"
#        elif (self.last_value == "on") :
#                self.api.switch_actor_on(int(self.base_pump))
#                print "Pump2 ON"
#        return {"value": self.last_value}

 #   def get_unit(self):
 #       return self.unit

    def stop(self):
        self.api.cache["mqtt"].client.unsubscribe(self.topic)
        SensorActive.stop(self)

    def execute(self):

        '''
        Active sensor has to handle his own loop
        :return:
        '''

        self.sleep(5)

@cbpi.initalizer(order=0)
def initBFMQTT(app):

    server = app.get_config_parameter("BF_MQTT_SERVER",None)
    if server is None:
        server = "localhost"
        cbpi.add_config_parameter("BF_MQTT_SERVER", "localhost", "text", "Brewfather MQTT Server")

    port = app.get_config_parameter("BF_MQTT_PORT", None)
    if port is None:
        port = "1883"
        cbpi.add_config_parameter("BF_MQTT_PORT", "1883", "text", "Brewfather MQTT Sever Port")

    username = app.get_config_parameter("BF_MQTT_USERNAME", None)
    if username is None:
        username = "username"
        cbpi.add_config_parameter("BF_MQTT_USERNAME", "username", "text", "Brewfather MQTT username")

    password = app.get_config_parameter("BF_MQTT_PASSWORD", None)
    if password is None:
        password = "password"
        cbpi.add_config_parameter("BF_MQTT_PASSWORD", "password", "text", "Brewfather MQTT password")

    tls = app.get_config_parameter("BF_MQTT_TLS", None)
    if tls is None:
        tls = "false"
        cbpi.add_config_parameter("BF_MQTT_TLS", "false", "text", "Brewfather MQTT TLS")

    deviceid = app.get_config_parameter("BF_MQTT_DEVICEID", None)
    if deviceid is None:
        deviceid = "deviceid"
        cbpi.add_config_parameter("BF_MQTT_DEVICEID", "Enter DeviceID", "text", "Brewfather MQTT DeviceID")

    app.cache["mqtt"] = BFMQTTThread(server,port,username, password, tls, deviceid)
    app.cache["mqtt"].daemon = True
    app.cache["mqtt"].start()
    
    def bfmqtt_reader(api):
        while True:
            try:
                m = q.get(timeout=0.1)
                #api.cache.get("sensors")[m.get("id")].instance.last_value = m.get("value")
                #api.receive_sensor_value(m.get("id"), m.get("value"))
            except:
                pass

    cbpi.socketio.start_background_task(target=bfmqtt_reader, api=app)
