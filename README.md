# Brewfather-plugin-dev

Brewfather MQTT Integration Plugin for CraftBeerPi 3.0

Installation
Install missing python lib
After installation please install python MQTT lib paho

pip install paho-mqtt

https://pypi.python.org/pypi/paho-mqtt/1.1

Configuration:

1. Set the following parameters under 'System - Parameter':

* BF_MQTT_PORT			- Port used for the MQTT connection.
* BF_MQTT_SERVER		- Servername used for the MQTT connection.
* BF_MQTT_TLS			- Certificate for the MQTT connection.
* BF_MQTT_USERNAME 		- Username for the MQTT connection.
* BF_MQTT_PASSWORD              - Password for the MQTT connection.

* BF_MQTT_DEVICEID              - Unique DeviceId of CraftBeerPi.
* BF_MQTT_HOMEBREWING_COMMANDS_TOPIC    - MQTT Homebrewing Commands Topic.
* BF_MQTT_HOMEBREWING_DYNAMICMASH_TOPIC - MQTT Homebrwing Dynamic/mash Topic.
* BF_MQTT_HOMEBREWING_DYNAMICHLT_TOPIC - MQTT Homebrewing Dynamic/HLT Topic.
* BF_MQTT_HOMEBREWING_RECIPES_TOPIC - MQTT Homebrewing Recipes Topic.
* BF_MQTT_HOMEBREWING_EVENTS_TOPIC - MQTT Homebrewing Events Topic.
* BF_MQTT_THERMOSTAT_COMMANDS_TOPIC    - MQTT Thermostat Commands Topic.
* BF_MQTT_THERMOSTAT_DYNAMIC_TOPIC    - MQTT Thermostat Dynamic Topic.
* BF_MQTT_THERMOSTAT_PROFILES_TOPIC    - MQTT Thermostat Profiles Topic.

2. Create Sensor under 'System - Hardware Settings':

* Name the sensor e.g. "BF MQTT Listener"
* [x] Hide on Dashboard.
* Choose "BF_MQTT_ListenerCommands" under 'Type'.
* Choose your mash kettle under 'Mash Kettle to control'
* Choose your HLT kettle under 'HLT kettle to control', if none leave blank.
* Press Add.
