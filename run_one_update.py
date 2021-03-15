import sys
import os
import json
import logging

from ruuvitag_sensor.ruuvi import RuuviTagSensor

temp_min = None
temp_max = None

if len(sys.argv) > 1:
    temp_max = float(sys.argv[1])
if len(sys.argv) > 2:
    temp_min = float(sys.argv[2])

print('Running with min max range: {} - {}'.format(temp_min, temp_max))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(filename)s: %(message)s')

problem = False

conf = json.loads(open('conf.json').read())

try:
    ruuvitag_mac_address = conf['ruuvitag_mac_address']

    logging.info(f'Loaded Ruuvi mac from conf: {ruuvitag_mac_address}')
    logging.info('Attempting ruuvi update...')
    ruuvi_data = RuuviTagSensor.get_data_for_sensors([ruuvitag_mac_address], 4)
    logging.info(f'Ruuvi data: {ruuvi_data}')

    if not ruuvitag_mac_address in ruuvi_data:
        raise RuntimeError('No result for ruuvi mac')

    temp_c = ruuvi_data[ruuvitag_mac_address]['temperature']
    temp_f = temp_c*180./100.+32.
    logging.info(f'Temperature in fahrenheit: {temp_f}')
    print(f'\n  --> {temp_f} deg F <--\n')
except KeyboardInterrupt: raise KeyboardInterrupt
except SystemExit: raise SystemExit
except Exception as e:
    logging.error(traceback.format_exc())
    problem = True

kasa_plug_alias = conf['kasa_plug_alias']
logging.info(f'Loaded kasa plug alias from conf: {kasa_plug_alias}')

# It's so stupid that I'm calling this via os.system but I couldn't get it working directly in Python for some reason.
kasa_command_prefix = f'kasa --alias "{kasa_plug_alias}" --plug '
if temp_max and (problem or temp_f >= temp_max):
    logging.info('Attempting to turn off...')
    logging.info(os.system(kasa_command_prefix+'off'))
if temp_min and temp_f <= temp_min:
    logging.info('Attempting to turn on...')
    logging.info(os.system(kasa_command_prefix+'on'))
logging.info('Querying plug status at end...')
os.system(kasa_command_prefix)
logging.info('Done')


