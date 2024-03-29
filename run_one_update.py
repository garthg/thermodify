import sys
import traceback
import os
import time
import json
import logging
from datetime import datetime

from ruuvitag_sensor.ruuvi import RuuviTagSensor


def hour_within_bounds(hour_target, hour_start, hour_end):
    if hour_start == hour_end:
        return True
    if hour_end > hour_start:
        return (hour_target >= hour_start and hour_target <= hour_end)
    else:
        return not (hour_target > hour_end and hour_target < hour_start)

def current_within_hour_bounds(hour_start, hour_end):
    local_now = datetime.now()
    logging.info(f'Current time: {local_now}')
    local_hour = local_now.hour
    logging.info(f'Assess {local_hour} between {hour_start} - {hour_end}')
    return hour_within_bounds(local_hour, hour_start, hour_end)
    
def _get_temperature(ruuvitag_mac_address):
    logging.info(f'Using Ruuvi mac: {ruuvitag_mac_address}')
    logging.info('Attempting ruuvi update...')
    ruuvi_data = RuuviTagSensor.get_data_for_sensors([ruuvitag_mac_address], 4)
    logging.info(f'Ruuvi data: {ruuvi_data}')
    if not ruuvitag_mac_address in ruuvi_data:
        raise RuntimeError('No result for ruuvi mac')
    temp_c = ruuvi_data[ruuvitag_mac_address]['temperature']
    temp_f = temp_c*180./100.+32.
    logging.info(f'Temperature in fahrenheit: {temp_f}')
    return temp_f

"""
Returns: tuple(is ok, temp Fahrenheit or None)
"""
def get_temperature(ruuvitag_mac_address):
    problem = False
    tries = 3
    sleep_secs = 5
    temp_f = None
    for i in range(tries):
        try:
            temp_f = _get_temperature(ruuvitag_mac_address)
            problem = False
            break
        except KeyboardInterrupt: raise KeyboardInterrupt
        except SystemExit: raise SystemExit
        except Exception as e:
            logging.error(traceback.format_exc())
            problem = True
            if i+1 < tries:
                logging.warn(f'Encountered error, sleeping for {sleep_secs} seconds...')
                time.sleep(sleep_secs)
    return (not problem, temp_f)
    
def run_one_update(temp_min, temp_max, ruuvitag_mac_address, kasa_plug_alias):
    result = {}
    ok, temp_f = get_temperature(ruuvitag_mac_address)
    problem = not ok
    result['temperature_f'] = temp_f
    print(f'\n  --> {temp_f} deg F <--\n')

    logging.info(f'Using kasa plug alias: {kasa_plug_alias}')
    # It's so stupid that I'm calling this via os.system but I couldn't get it working directly in Python for some reason.
    kasa_command_prefix = f'kasa --alias "{kasa_plug_alias}" --plug '
    kasa_change_command = None
    if temp_max and (problem or temp_f >= temp_max):
        logging.info('Request to turn off...')
        kasa_change_command = kasa_command_prefix+'off'
    if temp_min and temp_f <= temp_min:
        logging.info('Request to turn on...')
        kasa_change_command = kasa_command_prefix+'on'
    if kasa_change_command:
        logging.info(f'Attempting kasa command: {kasa_change_command}')
        logging.info(os.system(kasa_change_command))
    result['kasa_command'] = kasa_change_command
    logging.info('Querying plug status at end...')
    logging.info(os.system(kasa_command_prefix))
    logging.info('Done')
    return result

# returns (should_run, result)
def run_one_update_hour_bounds(hour_start, hour_end, temp_min, temp_max, ruuvitag_mac_address, kasa_plug_alias):
    should_run = False
    if current_within_hour_bounds(hour_start, hour_end):
        should_run = True
        result = run_one_update(temp_min, temp_max, ruuvitag_mac_address, kasa_plug_alias)
        return (should_run, result)
    logging.info('Outside of hour bounds, not checking.')
    return should_run, None

def print_current_temperature(ruuvitag_mac_address):
    _, temp_f = get_temperature(ruuvitag_mac_address)


# returns (should_run, result)
def run_one_thermostat_entry(thermostat_entry, ruuvitag_mac_address, kasa_plug_alias):
    temp_min = thermostat_entry['temp_min_f']
    temp_max = thermostat_entry['temp_max_f']
    hour_start = thermostat_entry['hour_start']
    hour_end = thermostat_entry['hour_end']
    print('Running in bounds: {} - {}'.format(hour_start, hour_end))
    print('Running with min max range: {} - {}'.format(temp_min, temp_max))
    should_run, result = run_one_update_hour_bounds(hour_start, hour_end, temp_min, temp_max, ruuvitag_mac_address, kasa_plug_alias)
    print(should_run, result)
    return should_run, result

def test():
    print('Running test')
    assert(hour_within_bounds(3,2,4))
    assert(hour_within_bounds(0,0,12))
    assert(hour_within_bounds(0,0,0))
    assert(hour_within_bounds(1,1,1))
    assert(hour_within_bounds(2,1,1))
    assert(hour_within_bounds(1,22,2))
    assert(hour_within_bounds(23,22,2))
    assert(hour_within_bounds(22,22,2))
    assert(hour_within_bounds(2,22,2))
    assert(hour_within_bounds(0,20,7))
    assert(not hour_within_bounds(5,2,4))
    assert(not hour_within_bounds(0,2,4))
    assert(not hour_within_bounds(21,22,2))
    assert(not hour_within_bounds(3,22,2))

    now_hour = datetime.now().hour
    assert(not current_within_hour_bounds((now_hour+2)%24, (now_hour+3)%24))
    assert(current_within_hour_bounds(0, 23))
    assert(current_within_hour_bounds(0, 0))
    assert(current_within_hour_bounds(now_hour, now_hour))
    assert(current_within_hour_bounds(now_hour, (now_hour+12)%24))



def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(filename)s: %(message)s')

    if len(sys.argv) <2:
        test()
        sys.exit(0)

    temp_min = None
    temp_max = None

    #if len(sys.argv) > 1:
    #    temp_max = float(sys.argv[1])
    #if len(sys.argv) > 2:
    #    temp_min = float(sys.argv[2])

    conf = json.loads(open('conf.json').read())
    ruuvitag_mac_address = conf['ruuvitag_mac_address']
    kasa_plug_alias = conf['kasa_plug_alias']

    thermostat_data = json.loads(open(sys.argv[1]).read())
    print(thermostat_data)
    for thermostat_entry in thermostat_data:
        should_run, result = run_one_thermostat_entry(thermostat_entry, ruuvitag_mac_address, kasa_plug_alias)
        if should_run:
            break
        else:
            print(result)


if __name__ == '__main__':
    main()
