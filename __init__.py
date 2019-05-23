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


@cbpi.actor
class MQTTActorJson(ActorBase):
    topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
    def on(self, power=100):
        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({"state": "on"}), qos=2, retain=True)

    def off(self):
        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({"state": "off"}), qos=2, retain=True)

@cbpi.actor
class MQTTControlObject(ActorBase):
    #topic = Property.Text("Topic", configurable=True, default_value="cbpi/homebrewing/MQTT_USERNAME/commands", description="MQTT TOPIC")
    topic = "cbpi/homebrewing/uuid/commands"
    object = Property.Text("Object", configurable=True, default_value="", description="Data Object, e.g. pump")
    def on(self, power=100):
        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({self.object: "on"}), qos=2, retain=True)

    def off(self):
        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({self.object: "off"}), qos=2, retain=True)

@cbpi.actor
class MQTTActorInt(ActorBase):
    topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
    def on(self, power=100):
        self.api.cache["mqtt"].client.publish(self.topic, payload=1, qos=2, retain=True)

    def off(self):
        self.api.cache["mqtt"].client.publish(self.topic, payload=0, qos=2, retain=True)

@cbpi.sensor
class MQTTListenerControlObject(SensorActive):
#    a_topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
    a_topic = "cbpi/homebrewing/uuid/commands"
    #b_payload = Property.Text("Object payload", configurable=True, default_value="", description="Object in patload, e.g. pump, leave blank for raw payload")
    base_pump = Property.Actor(label="Pump Actor", description="Select the Pump actor you would like to control from MQTT.")
    base_automatic = Property.Kettle(label="Kettle to control", description="Kettle you would like to control.")
    b_payload = "pump"

    last_value = None
    def init(self):
        self.topic = self.a_topic
        if self.b_payload == "":
            self.payload_text = None
        else:
            self.payload_text = self.b_payload.split('.')
        SensorActive.init(self)
        def on_message(client, userdata, msg):

            try:
                print "Payload from MQTT = " + msg.payload
		json_data = json.loads(msg.payload)
                print "Payload JSON = "
                print json_data
                val = json_data
                if self.payload_text is not None:
                    for key in self.payload_text:
                        val = val.get(key, None)
                print "VAL = " + val
                if isinstance(val, (int, float, basestring)):
                    q.put({"id": on_message.sensorid, "value": val})
            except Exception as e:
                print e
        on_message.sensorid = self.id
        self.api.cache["mqtt"].client.subscribe(self.topic)
        self.api.cache["mqtt"].client.message_callback_add(self.topic, on_message)


    def get_value(self):
        # Control base actor from MQTT.
        if (self.last_value == "off") :
                self.api.switch_actor_off(int(self.base_pump))
        elif (self.last_value == "on") :
                self.api.switch_actor_on(int(self.base_pump))

        return {"value": self.last_value}

    def get_unit(self):
        return self.unit

    def stop(self):
        self.api.cache["mqtt"].client.unsubscribe(self.topic)
        SensorActive.stop(self)

    def execute(self):

        '''
        Active sensor has to handle his own loop
        :return:
        '''

#	f.close()

        self.sleep(5)

@cbpi.sensor
class MQTTListenerControlActor(SensorActive):
    a_topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
    b_payload = Property.Text("Payload Dictioanry", configurable=True, default_value="", description="Where to find msg in patload, leave blank for raw payload")
    c_unit = Property.Text("Unit", configurable=True, default_value="", description="Units to display")
    base = Property.Actor(label="Base Actor", description="Select the actor you would like to control from MQTT.")

    last_value = None
    def init(self):
        self.topic = self.a_topic
        if self.b_payload == "":
            self.payload_text = None
        else:
            self.payload_text = self.b_payload.split('.')
        self.unit = self.c_unit[0:3]

        SensorActive.init(self)
        def on_message(client, userdata, msg):

            try:
                print "payload " + msg.payload
                json_data = json.loads(msg.payload)
                #print json_data
                print json_data
                val = json_data
                if self.payload_text is not None:
                    for key in self.payload_text:
                        val = val.get(key, None)
                #print val
                print val
                if isinstance(val, (int, float, basestring)):
                    q.put({"id": on_message.sensorid, "value": val})
            except Exception as e:
                print e
        on_message.sensorid = self.id
        self.api.cache["mqtt"].client.subscribe(self.topic)
        self.api.cache["mqtt"].client.message_callback_add(self.topic, on_message)

    def get_value(self):
        # Control base actor from MQTT.
        if (self.last_value == 0) :
                self.api.switch_actor_off(int(self.base))
#                self.api.switch_actor_on(int(self.base), power=power)
        elif (self.last_value == 1) :
                self.api.switch_actor_on(int(self.base))
#                self.api.switch_actor_on(int(self.base), power=power)
#        else:
#                self.api.switch_actor_off(int(self.base))

        return {"value": self.last_value, "unit": self.unit}

    def get_unit(self):
        return self.unit

    def stop(self):
        self.api.cache["mqtt"].client.unsubscribe(self.topic)
        SensorActive.stop(self)

    def execute(self):

        '''
        Active sensor has to handle his own loop
        :return:
        '''
        self.sleep(5)

@cbpi.sensor
class MQTTListenerControlStep(SensorActive):
    a_topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
    b_payload = Property.Text("Object in payload", configurable=True, default_value="", description="Object in patload, e.g. pump, leave blank for raw payload")
    #c_unit = Property.Text("Unit", configurable=True, default_value="", description="Units to display")
    
    last_value = None
    def init(self):
        self.topic = self.a_topic
        if self.b_payload == "":
            self.payload_text = None
        else:
            self.payload_text = self.b_payload.split('.')
        #self.unit = self.c_unit[0:3]

        SensorActive.init(self)
        def on_message(client, userdata, msg):

            try:
                print "payload " + msg.payload
                json_data = json.loads(msg.payload)
                #print json_data
                print json_data
                val = json_data
                if self.payload_text is not None:
                    for key in self.payload_text:
                        val = val.get(key, None)
                #print val
                print val
                if isinstance(val, (int, float, basestring)):
                    q.put({"id": on_message.sensorid, "value": val})
            except Exception as e:
                print e
        on_message.sensorid = self.id
        self.api.cache["mqtt"].client.subscribe(self.topic)
        self.api.cache["mqtt"].client.message_callback_add(self.topic, on_message)

    def get_value(self):
        # Control steo from MQTT.
        if (self.last_value == 0) :
                #StepView.stop()
		print "stop"
        elif (self.last_value == 1) :
                #StepView.start()
		print "start"

#        return {"value": self.last_value, "unit": self.unit}
        return {"value": self.last_value}

#    def get_unit(self):
#        return self.unit

    def stop(self):
        self.api.cache["mqtt"].client.unsubscribe(self.topic)
        SensorActive.stop(self)

    def execute(self):

        '''
        Active sensor has to handle his own loop
        :return:
        '''
        self.sleep(5)

@cbpi.sensor
class MQTTListenerKettleAuto(SensorActive):
    a_topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
    b_payload = Property.Text("Payload Dictioanry", configurable=True, default_value="", description="Where to find msg in patload, leave blank for raw payload")
    c_unit = Property.Text("Unit", configurable=True, default_value="", description="Units to display")
    kettleid = Property.Kettle(label="Kettle id", description="Select the Kettle id you would like to control from MQTT.")
	
    last_value = None
    def init(self):
        self.topic = self.a_topic
        if self.b_payload == "":
            self.payload_text = None
        else:
            self.payload_text = self.b_payload.split('.')
        self.unit = self.c_unit[0:3]

        SensorActive.init(self)
        def on_message(client, userdata, msg):

            try:
                print "payload " + msg.payload
                json_data = json.loads(msg.payload)
                #print json_data
                print json_data
                val = json_data
                if self.payload_text is not None:
                    for key in self.payload_text:
                        val = val.get(key, None)
                #print val
                print val
                if isinstance(val, (int, float, basestring)):
                    q.put({"id": on_message.sensorid, "value": val})
            except Exception as e:
                print e
        on_message.sensorid = self.id
        self.api.cache["mqtt"].client.subscribe(self.topic)
        self.api.cache["mqtt"].client.message_callback_add(self.topic, on_message)

    def get_value(self):
        # Control Kettle from MQTT.
        #if (self.last_value == 0) :
                #Kettle2View().toggle(kettleid)
		#Kettle2View().toggle(1)
	#	print "toggle"
        #elif (self.last_value == 1) :
                #Kettle2View().toggle(kettleid)
#		Kettle2View().toggle(1)
#		print "toggle"
	Kettle2View().toggle(1)	

        return {"value": self.last_value, "unit": self.unit}

    def get_unit(self):
        return self.unit

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

    cbpi.socketio.start_background_task(target=mqtt_reader, api=app)
