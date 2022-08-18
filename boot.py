import json
import captive_portal
import clock_config_server

try:
  wifi_config_file = open('wifi.json')

  wifi_config = json.load(wifi_config_file)

  print('Found wifi config file')
  print(wifi_config)

  clock_config_server.start()

except:
  print('No WIFI config file found, launching captive portal')
  captive_portal.start()