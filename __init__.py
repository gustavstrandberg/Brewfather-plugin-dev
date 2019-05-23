# -*- coding: utf-8 -*-
import paho.mqtt.client as mqtt
from eventlet import Queue
from modules import cbpi, app, ActorBase
from modules.core.hardware import SensorActive
import json
import os, re, threading, time
from modules.core.props import Property
import requests

q = Queue()

def on_connect(client, userdata, flags, rc):
    print("MQTT Connected" + str(rc))

class MQTTThread (threading.Thread):

    def __init__(self,server,port,username,password,tls):
        threading.Thread.__init__(self)
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.tls = tls

    client = None
    def run(self):
        self.client = mqtt.Client()
        self.client.on_connect = on_connect

        if self.username != "username" and self.password != "password":
            self.client.username_pw_set(self.username, self.password)
        
        if self.tls.lower() == 'true':
            self.client.tls_set_context(context=None)

        self.client.connect(str(self.server), int(self.port), 60)
        self.client.loop_forever()


@cbpi.backgroundtask(key='mqtt_listener', interval=1)
def mqtt_listener_background_task(self):

    def on_message(client, userdata, msg):
        topic=msg.topic
        msg_decode=str(msg.payload.decode("utf-8","ignore"))
        print("MQTT data Received",msg_decode)
        msg_in=json.loads(msg_decode)
                
        if "pump" in msg_in:
            if msg_in["pump"] == "on":
                print("Starting Pump, pump = ",msg_in["pump"])
                self.switch_actor_on(2) 
            if msg_in["pump"] == "off":
                print("Stopping Pump, pump = ",msg_in["pump"])
                self.switch_actor_off(2)

    topic="cbpi/homebrewing/uuid/commands"
    client=mqtt.Client("cbpi_mqtt_listener_test")
    client.on_message=on_message
    client.connect("localhost")
    client.loop_start()
    client.subscribe(topic)
    time.sleep(.1)
    client.loop_stop()
    client.disconnect()
    pass

@cbpi.initalizer(order=0)
def initMQTT(app):

    server = app.get_config_parameter("MQTT_SERVER",None)
    if server is None:
        server = "localhost"
        cbpi.add_config_parameter("MQTT_SERVER", "localhost", "text", "MQTT Server")

    port = app.get_config_parameter("MQTT_PORT", None)
    if port is None:
        port = "1883"
        cbpi.add_config_parameter("MQTT_PORT", "1883", "text", "MQTT Sever Port")

    username = app.get_config_parameter("MQTT_USERNAME", None)
    if username is None:
        username = "username"
        cbpi.add_config_parameter("MQTT_USERNAME", "username", "text", "MQTT username")

    password = app.get_config_parameter("MQTT_PASSWORD", None)
    if password is None:
        password = "password"
        cbpi.add_config_parameter("MQTT_PASSWORD", "password", "text", "MQTT password")

    tls = app.get_config_parameter("MQTT_TLS", None)
    if tls is None:
        tls = "false"
        cbpi.add_config_parameter("MQTT_TLS", "false", "text", "MQTT TLS")

    app.cache["mqtt"] = MQTTThread(server,port,username, password, tls)
    app.cache["mqtt"].daemon = True
    app.cache["mqtt"].start()
    
    def mqtt_reader(api):
        while True:
            try:
                m = q.get(timeout=0.1)
                api.cache.get("sensors")[m.get("id")].instance.last_value = m.get("value")
                api.receive_sensor_value(m.get("id"), m.get("value"))
            except:
                pass

#    cbpi.socketio.start_background_task(target=mqtt_reader, api=app)

