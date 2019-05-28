# Brewfather-plugin-dev

Brewfather MQTT Integration Plugin for CraftBeerPi 3.0

Configuration:

1. Set the following parameters under 'System - Parameter':

* BF_MQTT_COMMANDS_TOPIC 	- MQTT commands Topic.
* BF_MQTT_DEVICEID		- Unique DeviceId of CraftBeerPi.
* BF_MQTT_DYNAMICMASH_TOPIC	- MQTT dynamic/mash Topic.
* BF_MQTT_PASSWORD		- Password used for the MQTT connection.
* BF_MQTT_PORT			- Port used for the MQTT connection.
* BF_MQTT_SERVER		- Servername used for the MQTT connection.
* BF_MQTT_TLS			- Certificate for the MQTT connection.
* BF_MQTT_USERNAME 		- Username for the MQTT connection.

2. Create Sensor under 'System - Hardware Settings':

* Name the sensor e.g. "BF MQTT Listener"
* [x] Hide on Dashboard.
* Choose "BF_MQTT_ListenerCommands" under 'Type'.
* Choose your peater under 'Heater Actor'.
* Choose your kettle under 'Kettle to control'
* Choose your pump under 'Pump Actor'.
* Press Add.

