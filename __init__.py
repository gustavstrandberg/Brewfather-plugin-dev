# Brewfather CraftBeerPi3 plugin
# Control the brewing process in CraftBeerPi3 from Brewfather app.
# https://brewfather.app/
#
# Code is based on original MQTT Plugin of Manuel83.
# 
# -*- coding: utf-8 -*-
import paho.mqtt.client as mqtt
from eventlet import Queue
from modules import cbpi, app, ActorBase

#gs
from modules.core.hardware import SensorActive, ActorBase
#from modules.core.props import Property
from modules.steps import StepView
from modules.kettle import Kettle2View

from modules.core.props import Property, StepProperty
from modules.core.step import StepBase

#from modules import cbpi
import json
import os, re, threading, time
import requests
import pdb

q = Queue()
mashkettle_id = None
hltkettle_id = None

def on_connect(client, userdata, flags, rc):
    print("BF MQTT Connected" + str(rc))

class BF_MQTT_Thread (threading.Thread):

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

#@cbpi.actor
#class BF_MQTT_ControlObject(ActorBase):
#    topic = Property.Text("Topic", configurable=True, default_value="cbpi/homebrewing/uuid/commands", description="MQTT TOPIC")
#    object = Property.Text("Object", configurable=True, default_value="", description="Data Object, e.g. pump")
#    def on(self, power=100):
#        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({self.object: "on"}), qos=2, retain=True)
#
#    def off(self):
#        self.api.cache["mqtt"].client.publish(self.topic, payload=json.dumps({self.object: "off"}), qos=2, retain=True)
#
#@cbpi.actor
#class BF_MQTT_ActorInt(ActorBase):
#    topic = Property.Text("Topic", configurable=True, default_value="", description="MQTT TOPIC")
#    def on(self, power=100):
#        self.api.cache["mqtt"].client.publish(self.topic, payload=1, qos=2, retain=True)
#
#    def off(self):
#        self.api.cache["mqtt"].client.publish(self.topic, payload=0, qos=2, retain=True)

@cbpi.sensor
class BF_MQTT_ListenerCommands(SensorActive):
     
    base_mashkettle = Property.Kettle(label="Mash kettle to control", description="Select the Mash kettle you would like to control from Brewfather.")
    base_hltkettle = Property.Kettle(label="HLT Kettle to control", description="Select the HLT kettle you would like to control from Brewfather. If none leave blank.")

    def init(self):
        self.homebrewing_commands_topic = self.get_config_parameter("BF_MQTT_HOMEBREWING_COMMANDS_TOPIC", None) 
        self.thermostat_commands_topic = self.get_config_parameter("BF_MQTT_THERMOSTAT_COMMANDS_TOPIC", None) 
        self.homebrewing_events_topic = self.get_config_parameter("BF_MQTT_HOMEBREWING_EVENTS_TOPIC", None)
        self.homebrewing_recipes_topic = self.get_config_parameter("BF_MQTT_HOMEBREWING_RECIPES_TOPIC", None) + "/1"
        self.thermostat_profiles_1_topic = self.get_config_parameter("BF_MQTT_THERMOSTAT_PROFILES_TOPIC", None) + "/1"
        self.thermostat_profiles_2_topic = self.get_config_parameter("BF_MQTT_THERMOSTAT_PROFILES_TOPIC", None) + "/2"

        SensorActive.init(self)
       
        global mashkettle_id
        global hltkettle_id
        mashkettle_id = self.base_mashkettle
        hltkettle_id = self.base_hltkettle
        
#        fermenter1 = cbpi.cache.get("fermenter")[int(1)] 
#       fermenter2 = cbpi.cache.get("fermenter")[int(2)]

        def on_message_homebrewing_commands(client, userdata, msg):

            try:
                msg_decode=str(msg.payload.decode("utf-8","ignore"))
                msg_in=json.loads(msg_decode)

                print "=================================" 
                print("BF MQTT Homebrewing Data Received",msg_decode)
                print "=================================" 

                if "pump" in msg_in:
                    if msg_in["pump"] == "on":
                        #cbpi.switch_actor_on(int(self.base_pump))                                                  # needs refresh of web, why?
                        #self.power = 100
                        #actor_on(int(self.base_pump), int(self.power))
                        mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)] 
                        requests.post("http://localhost:5000/api/actor/" + mashkettle.agitator + "/switch/on", timeout = 1)
                        if mashkettle.state == False:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "pump on"}), qos=1, retain=True)
                        else:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "pump on"}), qos=1, retain=True)
                    if msg_in["pump"] == "off":
                        #self.api.switch_actor_off(int(self.base_pump))                                             # needs refresh of web, why?
                        #self.actor_off(int(self.actor))
                        mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)] 
                        requests.post("http://localhost:5000/api/actor/" + mashkettle.agitator + "/switch/off", timeout = 1)
                        if mashkettle.state == False:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "pump auto"}), qos=1, retain=True)
                        else:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "pump auto"}), qos=1, retain=True)
                
                if "start" in msg_in:
                    if msg_in["start"] == "auto":
                        mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)]
                        if mashkettle.state == False:
                            requests.post("http://localhost:5000/api/kettle/" + self.base_mashkettle + "/automatic", timeout = 1) 
                            self.sleep(.1) 

#                pdb.set_trace()

                if "recipe" in msg_in:
                    if msg_in["recipe"] == 1:
                        requests.post("http://localhost:5000/api/step/start", timeout = 1)
                        self.sleep(.1)
                        requests.post("http://localhost:5000/api/step/action/start", timeout = 1)
                        self.sleep(.1) 
                        mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)]
                        if mashkettle.state == False:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"time":0, "event": "recipe 1"}), qos=1, retain=True)
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"time":0, "event": "start"}), qos=1, retain=True) 
                        else:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"time":0, "event": "recipe 1"}), qos=1, retain=True)
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"time":0, "event": "start"}), qos=1, retain=True)

                if "stop" in msg_in:
                    if msg_in["stop"] == True:
                        requests.post("http://localhost:5000/api/step/reset", timeout = 1)
                        self.sleep(.1)
                        mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)]
                        if mashkettle.state == True:
                            requests.post("http://localhost:5000/api/kettle/" + self.base_mashkettle + "/automatic", timeout = 1)
                            self.sleep(.1) 
                        requests.post("http://localhost:5000/api/actor/" + mashkettle.agitator + "/switch/off", timeout = 1)
                        self.sleep(.1) 
                        if mashkettle.state == False: 
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "stop"}), qos=1, retain=True)
                        else:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "stop"}), qos=1, retain=True)

                if "pause" in msg_in:
                    if msg_in["pause"] == True:
                        mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)]
                        if mashkettle.state == True:
                            requests.post("http://localhost:5000/api/kettle/" + self.base_mashkettle + "/automatic", timeout = 1)
                            self.sleep(.01)
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "pause"}), qos=1, retain=True)
                        else:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "pause"}), qos=1, retain=True)
                        requests.post("http://localhost:5000/api/actor/" + msshkettle.agitator+ "/switch/off", timeout = 1)
                        self.sleep(.1) 
                        self.pause = True 
                    
                    if msg_in["pause"] == False:
                        mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)]
                        if mashkettle.state == False:
                            requests.post("http://localhost:5000/api/kettle/" + self.base_mashkettle + "/automatic", timeout = 1)
                            self.sleep(.01) 
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "resume"}), qos=1, retain=True)
                        else:
                            self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "resume"}), qos=1, retain=True)
                        #requests.post("http://localhost:5000/api/actor/" + mashkettle.agitator + "/switch/on", timeout = 1)
                        self.pause = False

                if "mash SP" in msg_in:
                    self.settemp = str(msg_in["mash SP"])
                    requests.post("http://localhost:5000/api/kettle/" + self.base_mashkettle + "/targettemp/"  + self.settemp, timeout = 1)
                    self.sleep(.01) 
                    # figure out how to get and set countdown time and set it with temp.
                    mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)]
                    if mashkettle.state == False:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "Set Target Temp = " + self.settemp}), qos=1, retain=True)
                    else:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "Set Target Temp = " + self.settemp}), qos=1, retain=True)

                if "PWM" in msg_in:
                    self.pwm = str(msg_in["PWM"])
                    mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)]
                    requests.post("http://localhost:5000/api/actor/"  + mashhkettle.heater + "/power/" + self.pwm, timeout = 1)
                    if mashkettle.state == False:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "Set Power = " + self.pwm}), qos=1, retain=True)
                    else:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "Set Power = " + self.pwm}), qos=1, retain=True)
                    #self.actor_power(int(self.actor), self.power)

                if "HLT SP" in msg_in: 
                    self.hltsp = str(msg_in["HLT SP"])
                    requests.post("http://localhost:5000/api/actor/"  + self.base_hltkettle + "/targettemp/"  + self.hltsp, timeout = 1)
                    self.sleep(.01)
                    hltkettle = cbpi.cache.get("kettle")[int(self.base_hltkettle)]
                    if hltkettle.state == False:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "Set HLT Target Temp = " + self.hltsp}), qos=1, retain=True)
                    else:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "Set HLT Target Temp = " + self.hltsp}), qos=1, retain=True)

                if "countdown" in msg_in:
                    self.countdown = str(msg_in["countdown"])
                    mashkettle = cbpi.cache.get("kettle")[int(self.base_mashkettle)] 
                    countdown_simple_recipe_data = {"name" : "Brewfather Single Step",
                        "steps" : [
                            {"name" : "Brewfather Single Step", "type" : "MASH", "timer" : self.countdown ,"temp" : mashkettle.target_temp}
                        ]
                    }
                    requests.post("http://localhost:5000/api/recipe/import/v1/", data=json.dumps(countdown_simple_recipe_data), headers = {'Content-Type':'application/json'}, timeout = 1 )
                    time.sleep(.01)
                    requests.post("http://localhost:5000/api/step/reset", timeout = 1)
                    time.sleep(.01)
                    if mashkettle.state == False:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/manual", payload=json.dumps({"event": "Set Countdown = " + self.countdown}), qos=1, retain=True)
                    else:
                        self.api.cache["mqtt"].client.publish(self.homebrewing_events_topic + "/auto", payload=json.dumps({"event": "Set Countdown = " + self.countdown}), qos=1, retain=True)


            except Exception as e:
                print e
        
        def on_message_thermostat_commands(client, userdata, msg):
            try:
                msg_decode=str(msg.payload.decode("utf-8","ignore"))
                msg_in=json.loads(msg_decode)
                print "================================="
                print("BF MQTT Thermostat Data Received",msg_decode)
                print "================================="

                if "stop" in msg_in:
                    if msg_in["stop"] == True:
                        fermenter1 = cbpi.cache.get("fermenter")[int(1)]
                        if fermenter1.state == True:
                            requests.post("http://localhost:5000/api/fermenter/1/automatic", timeout = 1)
                        fermenter2 = cbpi.cache.get("fermenter")[int(2)]
                        if fermenter2.state == True:
                            requests.post("http://localhost:5000/api/fermenter/2/automatic", timeout = 1)

                if "start" in msg_in:
                    if msg_in["start"] == "advanced" and msg_in["CH1 profile"] == 1:
                        fermenter1 = cbpi.cache.get("fermenter")[int(1)]
                        requests.post("http://localhost:5000/api/fermenter/1/brewname", data=json.dumps({"brewname":"Brewfather CH1"}), timeout = 1)
                        if fermenter1.state == False: 
                            requests.post("http://localhost:5000/api/fermenter/1/automatic", timeout = 1)
                    if msg_in["start"] == "advanced" and msg_in["CH2 profile"] == 2:
                        fermenter2 = cbpi.cache.get("fermenter")[int(2)]
                        if fermenter2.state == False:
                            requests.post("http://localhost:5000/api/fermenter/2/automatic", timeout = 1)

                if "CH1 SP" in msg_in:
                    self.settemp = str(msg_in["CH1 SP"])
                    requests.post("http://localhost:5000/api/fermenter/1/targettemp/"  + self.settemp, timeout = 1)
                    requests.post("http://localhost:5000/api/fermenter/1/step", data=json.dumps({"fermenter_id":1,"name":"BF CH1 Time","temp":self.settemp,"days":"","minutes":"","hours":""}) , timeout = 1)

                if "CH2 SP" in msg_in:
                    self.settemp = str(msg_in["CH2 SP"])
                    requests.post("http://localhost:5000/api/fermenter/2/targettemp/"  + self.settemp, timeout = 1)

                if "CH1 countdown" in msg_in:
                    self.settime = int(msg_in["CH1 countdown"])
                    self.settime_days = (self.settime / 1440)  
                    self.settime_hours = (self.settime / 60) % 24 
                    self.settime_minutes = self.settime % 60 
                   
                    profiles_1_data = {
                        "fermenter_id" : 1,
                        "name" : "BF CH1 Simple Step",
                        "temp" : "",
                        "days" : self.settime_days,
                        "minutes" : self.settime_minutes,
                        "hours" : self.settime_hours
                    }
                    # delete all fermenter profiles
                    #fermenter1 = cbpi.cache.get("fermenter")[int(1)]
                    #for idx, value in cbpi.cache["fermenter"].iteritems():
                    #    try:
                    #        if value.id == int(fermenter1.id):
                    #            print "value.steps = ", value.steps
                    #            print "value__dics__._keys() = ", value.__dict__.keys()
                    #    except  Exception as e:
                    #        print e
                    for x in range(15):
                        requests.delete("http://localhost:5000/api/fermenter/1/step/x", timeout = 1)
                        time.sleep(.01)
                    requests.post("http://localhost:5000/api/fermenter/1/step", data=json.dumps(profiles_1_data), headers = {'Content-Type':'application/json'}, timeout = 1)
                    time.sleep(.01)

                if "CH2 countdown" in msg_in:
                    self.settime = int(msg_in["CH2 countdown"])
                    self.settime_days = (self.settime / 1440)
                    self.settime_hours = (self.settime / 60) % 24
                    self.settime_minutes = self.settime % 60
                    profiles_2_data = {
                        "fermenter_id" : 2,
                        "name" : "BF CH2 Simple Step",
                        "temp" : "",
                        "days" : self.settime_days,
                        "minutes" : self.settime_minutes,
                        "hours" : self.settime_hours
                    }
                    for x in range(15):
                        requests.delete("http://localhost:5000/api/fermenter/2/step/x", timeout = 1)
                        time.sleep(.01)
                    requests.post("http://localhost:5000/api/fermenter/2/step", data=json.dumps(profiles_2_data), headers = {'Content-Type':'application/json'}, timeout = 1)
                    time.sleep(.01)

            except Exception as e:
                print e
        
        def on_message_homebrewing_recipe(client, userdata, msg):
            try:
                msg_decode=str(msg.payload.decode("utf-8","ignore"))
                msg_in=json.loads(msg_decode)
                print "================================="
                print("BF MQTT RECPIE = ",msg_decode)
                print "================================="
                if "mash in temp" in msg_in:
                    self.mashintemp = msg_in["mash in temp"]
                    self.mash1temp = msg_in["phytase temp"]
                    self.mash1time = msg_in["phytase time"]
                    self.mash2temp = msg_in["glucanase temp"]
                    self.mash2time = msg_in["glucanase time"]
                    self.mash3temp = msg_in["protease temp"]
                    self.mash3time = msg_in["protease time"]
                    self.mash4temp = msg_in["B-amylase temp"]
                    self.mash4time = msg_in["B-amylase time"]
                    self.mash5temp = msg_in["A-amylase 1 temp"]
                    self.mash5time = msg_in["A-amylase 1 time"]
                    self.mash6temp = msg_in["A-amylase 2 temp"]
                    self.mash6time = msg_in["A-amylase 2 time"]
                    self.mashouttemp = msg_in["mash out temp"]
                    self.mashouttime = msg_in["mash out time"]
                    self.boiltime = msg_in["boil time"]
                    self.hopadd = msg_in["hop additions"]
                    self.hop1time = msg_in["hop 1 time"]
                    self.hop2time = msg_in["hop 2 time"]
                    self.hop3time = msg_in["hop 3 time"]
                    self.hop4time = msg_in["hop 4 time"]
                    self.hop5time = msg_in["hop 5 time"]
                
                recipe_data = {"name" : "Brewfather Recipe",
                    "steps" : [
                        {"name" : "Mash In", "type" : "MASH", "timer" : 1 ,"temp" : self.mashintemp},
                        {"name" : "Mash Step 1", "type" : "MASH", "timer" : self.mash1time ,"temp" : self.mash1temp},
                        {"name" : "Mash Step 2", "type" : "MASH", "timer" : self.mash2time ,"temp" : self.mash2temp},
                        {"name" : "Mash Step 3", "type" : "MASH", "timer" : self.mash3time ,"temp" : self.mash3temp},
                        {"name" : "Mash Step 4", "type" : "MASH", "timer" : self.mash4time ,"temp" : self.mash4temp},
                        {"name" : "Mash Step 5", "type" : "MASH", "timer" : self.mash5time ,"temp" : self.mash5temp},
                        {"name" : "Mash Step 6", "type" : "MASH", "timer" : self.mash6time ,"temp" : self.mash6temp},
                        {"name" : "Mash Out", "type" : "MASH", "timer" : self.mashouttime ,"temp" : self.mashouttemp},
                        {"name" : "Boil Step", "type" : "BOIL", "timer" : self.boiltime ,"temp" : 100}
                    ]
                }
                
                requests.post("http://localhost:5000/api/recipe/import/v1/", data=json.dumps(recipe_data), headers = {'Content-Type':'application/json'}, timeout = 1 )
                time.sleep(.01)
                requests.post("http://localhost:5000/api/step/reset", timeout = 1)
                time.sleep(.01)

            except Exception as e:
                print e

        def on_message_thermostat_profiles_1(client, userdata, msg):
            try:
                msg_decode=str(msg.payload.decode("utf-8","ignore"))
                msg_in=json.loads(msg_decode)
                print "================================="
                print("BF MQTT Profile1 Data Received",msg_decode)
                print "================================="
                if "SP1" in msg_in:
                    self.SP1 = msg_in["SP1"]
                    self.soak1 = msg_in["soak1"]
                    self.ramp1 = msg_in["ramp1"]
                    self.SP2 = msg_in["SP2"]
                    self.soak2 = msg_in["soak2"]
                    self.ramp2 = msg_in["ramp2"]
                    self.SP3 = msg_in["SP3"]
                    self.soak3 = msg_in["soak3"]
                    self.ramp3 = msg_in["ramp3"]
                    self.SP4 = msg_in["SP4"]
                    self.soak4 = msg_in["soak4"]
                    self.ramp4 = msg_in["ramp4"]
                    self.SP5 = msg_in["SP5"]
                    self.soak5 = msg_in["soak5"]
                    self.ramp5 = msg_in["ramp5"]
                    self.SP6 = msg_in["SP6"]
                    self.soak6 = msg_in["soak6"]
                    self.ramp6 = msg_in["ramp6"]
                    self.SP7 = msg_in["SP7"]
                    self.soak7 = msg_in["soak7"]
                    self.ramp7 = msg_in["ramp7"]
                    self.SP8 = msg_in["SP8"]
                
                self.settime_days = (self.soak1 / 86400)
                self.settime_hours = (self.soak1 / 3600) % 24
                self.settime_minutes = self.soak1 % 60 

                profiles_1_data = {
                    "fermenter_id" : 1,
                    "name" : "BF CH1 Step 1",
                    "temp" : self.SP1,
                    "days" : self.settime_days,
                    "minutes" : self.settime_minutes,
                    "hours" : self.settime_hours
                }
                
                # find better method to delete all steps
                # make loop to add steps with ramp.
                try:
                    for xx in range(0, 10, 1):
                        requests.delete("http://localhost:5000/api/fermenter/1/step/" + str(xx), timeout = 1)
                        time.sleep(.02)
                except Exception as e:
                    print e
                try:
                    for xx in range(10, 20, 1):
                        requests.delete("http://localhost:5000/api/fermenter/1/step/" + str(xx), timeout = 1)
                        time.sleep(.02)
                except Exception as e:
                    print e

                requests.post("http://localhost:5000/api/fermenter/1/step", data=json.dumps(profiles_1_data), headers = {'Content-Type':'application/json'}, timeout = 1)
                time.sleep(.01)

            except Exception as e:
                print e

        def on_message_thermostat_profiles_2(client, userdata, msg):
            try:
                msg_decode=str(msg.payload.decode("utf-8","ignore"))
                msg_in=json.loads(msg_decode)
                print "================================="
                print("BF MQTT Profile2 Data Received",msg_decode)
                print "================================="
                if "SP1" in msg_in:
                    self.SP1 = msg_in["SP1"]
                    self.soak1 = msg_in["soak1"]
                    self.ramp1 = msg_in["ramp1"]
                    self.SP2 = msg_in["SP2"]
                    self.soak2 = msg_in["soak2"]
                    self.ramp2 = msg_in["ramp2"]
                    self.SP3 = msg_in["SP3"]
                    self.soak3 = msg_in["soak3"]
                    self.ramp3 = msg_in["ramp3"]
                    self.SP4 = msg_in["SP4"]
                    self.soak4 = msg_in["soak4"]
                    self.ramp4 = msg_in["ramp4"]
                    self.SP5 = msg_in["SP5"]
                    self.soak5 = msg_in["soak5"]
                    self.ramp5 = msg_in["ramp5"]
                    self.SP6 = msg_in["SP6"]
                    self.soak6 = msg_in["soak6"]
                    self.ramp6 = msg_in["ramp6"]
                    self.SP7 = msg_in["SP7"]
                    self.soak7 = msg_in["soak7"]
                    self.ramp7 = msg_in["ramp7"]
                    self.SP8 = msg_in["SP8"]

                self.settime_days = (self.soak1 / 86400)
                self.settime_hours = (self.soak1 / 3600) % 24
                self.settime_minutes = self.soak1 % 60

                profiles_2_data = {
                    "fermenter_id" : 2,
                    "name" : "BF CH1 Step 1",
                    "temp" : self.SP1,
                    "days" : self.settime_days,
                    "minutes" : self.settime_minutes,
                    "hours" : self.settime_hours
                }

                # find better method to delete all steps
                # make loop to add steps with ramp.
                try:
                    for xx in range(0, 10, 1):
                        requests.delete("http://localhost:5000/api/fermenter/2/step/" + str(xx), timeout = 1)
                        time.sleep(.02)
                except Exception as e:
                    print e
                try:
                    for xx in range(10, 20, 1):
                        requests.delete("http://localhost:5000/api/fermenter/2/step/" + str(xx), timeout = 1)
                        time.sleep(.02)
                except Exception as e:
                    print e

                requests.post("http://localhost:5000/api/fermenter/2/step", data=json.dumps(profiles_2_data), headers = {'Content-Type':'application/json'}, timeout = 1)
                time.sleep(.01)

            except Exception as e:
                print e


        self.api.cache["mqtt"].client.subscribe(self.homebrewing_commands_topic)
        self.api.cache["mqtt"].client.message_callback_add(self.homebrewing_commands_topic, on_message_homebrewing_commands)
        
        self.api.cache["mqtt"].client.subscribe(self.thermostat_commands_topic)
        self.api.cache["mqtt"].client.message_callback_add(self.thermostat_commands_topic, on_message_thermostat_commands)

        self.api.cache["mqtt"].client.subscribe(self.homebrewing_recipes_topic)
        self.api.cache["mqtt"].client.message_callback_add(self.homebrewing_recipes_topic, on_message_homebrewing_recipe)

        self.api.cache["mqtt"].client.subscribe(self.thermostat_profiles_1_topic)
        self.api.cache["mqtt"].client.message_callback_add(self.thermostat_profiles_1_topic, on_message_thermostat_profiles_1)
        self.api.cache["mqtt"].client.subscribe(self.thermostat_profiles_2_topic)
        self.api.cache["mqtt"].client.message_callback_add(self.thermostat_profiles_2_topic, on_message_thermostat_profiles_2)

    def stop(self):
        self.api.cache["mqtt"].client.unsubscribe(self.homebrewing_commands_topic)
        self.api.cache["mqtt"].client.unsubscribe(self.thermostat_commands_topic) 
        self.api.cache["mqtt"].client.unsubscribe(self.homebrewing_recipes_topic)
        self.api.cache["mqtt"].client.unsubscribe(self.thermostat_profiles1_topic)
        self.api.cache["mqtt"].client.unsubscribe(self.thermostat_profiles2_topic)
        SensorActive.stop(self)

    def execute(self):
        self.sleep(5)

@cbpi.backgroundtask(key='BFMQTT_DynamicMash', interval=1)                      
def BFMQTT_DynamicMash_background_task(self):

    global mashkettle_id
    global hltkettle_id

    self.homebrewing_dynamicmash_topic = cbpi.get_config_parameter("BF_MQTT_HOMEBREWING_DYNAMICMASH_TOPIC", None)
    self.homebrewing_dynamichlt_topic = cbpi.get_config_parameter("BF_MQTT_HOMEBREWING_DYNAMICHLT_TOPIC", None)

    self.mash = None
    self.HLT = None
    self.Fermenter1 = None
    self.Fermenter2 = None
    #step = cbpi.cache.get("active_step")
    #kettle = cbpi.cache.get("kettle")
    
    for idx, value in cbpi.cache["kettle"].iteritems():
        try:
            if value.id == int(mashkettle_id):
                self.mash = True 
                self.mash_target_temp = value.target_temp
                self.mash_current_temp = cbpi.get_sensor_value(value.sensor)
                if value.state == True:
                    self.mash_mode = "auto"
                if value.state == False:
                    self.mash_mode = "manual"
        except:
            self.mash = False

        try: 
            if value.id ==  int(hltkettle_id):
                self.HLT = True 
                self.hlt_target_temp = value.target_temp
                self.hlt_current_temp = cbpi.get_sensor_value(value.sensor)
                if value.state == True:
                    self.hlt_mode = "auto"
                if value.state == False:
                    self.hlt_mode = "manual"
        except:
            self.HLT = False    

    for idx, value in cbpi.cache["actors"].iteritems():
        try:
            mashkettle = cbpi.cache.get("kettle")[int(mashkettle_id)]
            if value.id == int(mashkettle.agitator):
                if value.state == 1:
                    self.pump_state = "on"
                if value.state == 0:
                    self.pump_state = "off"
            if value.id == int(mashkettle.heater):
                if value.state == 1:
                    self.mash_heater = value.power
                if value.state == 0:
                    self.mash_heater = "0"
        except:
            self.mash = False

        try:
            hltkettle = cbpi.cache.get("kettle")[int(hltkettle_id)]
            if value.id == int(hltkettle.heater):
                if value.state == 1:
                    self.hlt_heater = value.power
                if value.state == 0:
                    self.hlt_heater = "0"
        except:
            self.HLT = False

    if self.mash:
        dynamic_mash_data = {                                                          # define the playload
        'time': 0,
        'countdown': 0,
        'countup': 0,
        'pump': self.pump_state,
        'SP': self.mash_target_temp,
        'heater': self.mash_heater,
        'mode': self.mash_mode,
        'temp': self.mash_current_temp,
        'unit': cbpi.get_config_parameter("unit", None) 
        } 
  
        self.cache["mqtt"].client.publish(self.homebrewing_dynamicmash_topic, payload=json.dumps(dynamic_mash_data), qos=0, retain=True)

    if self.HLT:
        dynamic_hlt_data = {                                                          # define the playload
        'time': 0,
        'SP': self.hlt_target_temp,
        'heater': self.hlt_heater,
        'mode': self.hlt_mode,
        'temp': self.hlt_current_temp,
        'unit': cbpi.get_config_parameter("unit", None)
        }

        self.cache["mqtt"].client.publish(self.homebrewing_dynamichlt_topic, payload=json.dumps(dynamic_hlt_data), qos=0, retain=True)

@cbpi.backgroundtask(key='BFMQTT_Thermostat_Dynamic', interval=1)
def BFMQTT_Thermostat_Dynamic_background_task(self):

        self.thermostat_dynamic_1_topic = cbpi.get_config_parameter("BF_MQTT_THERMOSTAT_DYNAMIC_TOPIC", None) + "/CH1"
        self.thermostat_dynamic_2_topic = cbpi.get_config_parameter("BF_MQTT_THERMOSTAT_DYNAMIC_TOPIC", None) + "/CH2"

        self.fermenter1 = None
        self.fermenter2 = None
        self.fermenter1_mode = None
        self.fermenter2_mode = None

        for idx, value in cbpi.cache["fermenter"].iteritems():
            try:
                if value.id == int(1):
                    self.fermenter1 = True
                    self.fermenter1_current_temp = cbpi.get_sensor_value(value.sensor)
                    if value.state  == True:
                        self.fermenter1_runmode = "advanced"
                    if value.state == False:
                        self.fermenter1_runmode = "off"
            except:
                self.fermenter1 = False
            try:
                if value.id == int(2):
                    self.fermenter2 = True
                    self.fermenter2_current_temp = cbpi.get_sensor_value(value.sensor)
                    if value.state  == True:
                        self.fermenter2_runmode = "advanced"
                    if value.state == False:
                        self.fermenter2_runmode = "off"
            except:
                self.fermenter2 = False

        for idx, value in cbpi.cache["actors"].iteritems():
            try:
                fermenter1 = cbpi.cache.get("fermenter")[int(1)]
                if value.id == int(fermenter1.cooler):
                    if value.state == 1:
                        self.fermenter1_mode = "cooling"
                if value.id == int(fermenter1.heater):
                    if value.state == 1:
                        self.fermenter1_mode = "heating"
                        self.fermenter1_pwm = value.power
                    if value.state == 0:
                        self.fermenter1_pwm = "0"
            except:
                self.fermenter1 = False
            try:
                fermenter2 = cbpi.cache.get("fermenter")[int(2)]
                if value.id == int(fermenter2.cooler):
                    if value.state == 1:
                        self.fermenter2_mode = "cooling"
                if value.id == int(fermenter2.heater):
                    if value.state == 1:
                        self.fermenter2_mode = "heating"
                        self.fermenter2_pwm = value.power
                    if value.state == 0:
                        self.fermenter2_pwm = "0"
            except:
                self.fermenter2 = False

        if self.fermenter1:
            dynamic_1_data = {
                'time': 0,
                'countdown': 0,
                'countup': 0,
                'SP': fermenter1.target_temp,
                'mode': self.fermenter1_mode,
                'runmode': self.fermenter1_runmode,
                'temp': self.fermenter1_current_temp,
                'unit': cbpi.get_config_parameter("unit", None),
                'pwm': self.fermenter1_pwm
            }
            self.cache["mqtt"].client.publish(self.thermostat_dynamic_1_topic, payload=json.dumps(dynamic_1_data), qos=0, retain=True)

        if self.fermenter2:
            dynamic_2_data = {
                'time': 0,
                'countdown': 0,
                'countup': 0,
                'SP': fermenter2.target_temp,
                'mode': self.fermenter2_mode,
                'runmode': self.fermenter2_runmode,
                'temp': self.fermenter2_current_temp,
                'unit': cbpi.get_config_parameter("unit", None),
                'pwm': self.fermenter2_pwm
            }
            self.cache["mqtt"].client.publish(self.thermostat_dynamic_2_topic, payload=json.dumps(dynamic_2_data), qos=0, retain=True)

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
        deviceid = "*_Enter Device ID_*"
        cbpi.add_config_parameter("BF_MQTT_DEVICEID", "*_Enter Device ID_*", "text", "Brewfather MQTT DeviceID")

    homebrewing_commands_topic = app.get_config_parameter("BF_MQTT_HOMEBREWING_COMMANDS_TOPIC", None)
    if homebrewing_commands_topic is None:
        homebrewing_commands_topic = "cbpi/homebrewing/" + deviceid + "/commands"
        cbpi.add_config_parameter("BF_MQTT_HOMEBREWING_COMMANDS_TOPIC", "cbpi/homebrewing/" + deviceid + "/commands", "text", "Brewfather MQTT Homebrewing Commands Topic")

    thermostat_commands_topic = app.get_config_parameter("BF_MQTT_THERMOSTAT_COMMANDS_TOPIC", None)
    if thermostat_commands_topic is None:
        thermostat_commands_topic = "cbpi/thermostat/" + deviceid + "/commands"
        cbpi.add_config_parameter("BF_MQTT_THERMOSTAT_COMMANDS_TOPIC", "cbpi/thermostat/" + deviceid + "/commands", "text", "Brewfather MQTT Thermostat Commands Topic")
        
    homebrewing_events_topic = app.get_config_parameter("BF_MQTT_HOMEBREWING_EVENTS_TOPIC", None)
    if homebrewing_events_topic is None:
        homebrewing_events_topic = "cbpi/homebrewing/" + deviceid + "/events"
        cbpi.add_config_parameter("BF_MQTT_HOMEBREWING_EVENTS_TOPIC", "cbpi/homebrewing/" + deviceid + "/events", "text", "Brewfather MQTT Homebrewing Events Topic")

    homebrewing_dynamicmash_topic = app.get_config_parameter("BF_MQTT_HOMEBREWING_DYNAMICMASH_TOPIC", None)
    if homebrewing_dynamicmash_topic is None:
        homebrewing_dynamicmash_topic = "cbpi/homebrewing/" + deviceid + "/dynamic/mash"
        cbpi.add_config_parameter("BF_MQTT_HOMEBREWING_DYNAMICMASH_TOPIC", "cbpi/homebrewing/" + deviceid + "/dynamic/mash", "text", "Brewfather MQTT Homebrewing Dynamic Mash Topic")

    homebrewing_dynamichlt_topic = app.get_config_parameter("BF_MQTT_HOMEBREWING_DYNAMICHLT_TOPIC", None)
    if homebrewing_dynamichlt_topic is None:
        homebrewing_dynamichlt_topic = "cbpi/homebrewing/" + deviceid + "/dynamic/HLT"
        cbpi.add_config_parameter("BF_MQTT_HOMEBREWING_DYNAMICHLT_TOPIC", "cbpi/homebrewing/" + deviceid + "/dynamic/HLT", "text", "Brewfather MQTT Homebrewing Dynamic HLT Topic")

    homebrewing_recipes_topic = app.get_config_parameter("BF_MQTT_HOMEBREWING_RECIPES_TOPIC", None)
    if homebrewing_recipes_topic is None:
        homebrewing_recipes_topic = "cbpi/homebrewing/" + deviceid + "/recipes/update"
        cbpi.add_config_parameter("BF_MQTT_HOMEBREWING_RECIPES_TOPIC", "cbpi/homebrewing/" + deviceid + "/recipes/update", "text", "Brewfather MQTT Homebrewing Recipes Topic")

    thermostat_dynamic_topic = app.get_config_parameter("BF_MQTT_THERMOSTAT_DYNAMIC_TOPIC", None)
    if thermostat_dynamic_topic is None:
        thermostat_dynamic_topic = "cbpi/thermostat/" + deviceid + "/dynamic"
        cbpi.add_config_parameter("BF_MQTT_THERMOSTAT_DYNAMIC_TOPIC", "cbpi/thermostat/" + deviceid + "/dynamic", "text", "Brewfather MQTT Thermostat Dynamic Topic")

    thermostat_profiles_topic = app.get_config_parameter("BF_MQTT_THERMOSTAT_PROFILES_TOPIC", None)
    if thermostat_profiles_topic is None:
        thermostat_profiles_topic = "cbpi/thermostat/" + deviceid + "/profiles/update"
        cbpi.add_config_parameter("BF_MQTT_THERMOSTAT_PROFILES_TOPIC", "cbpi/thermostat/" + deviceid + "/profiles/update", "text", "Brewfather MQTT Thermostat Profiles Topic")

    app.cache["mqtt"] = BF_MQTT_Thread(server,port,username, password, tls, deviceid)
    app.cache["mqtt"].daemon = True
    app.cache["mqtt"].start()
    
    def bfmqtt_reader(api):
        while True:
            try:
                m = q.get(timeout=0.1)
            except:
                pass

    cbpi.socketio.start_background_task(target=bfmqtt_reader, api=app)
