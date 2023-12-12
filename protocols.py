import requests
import time
import concurrent.futures
from datetime import datetime
from pyvin import VIN


commands = {
    0: "'SHIPMODE'",  # Fully power down device, clears engine data information and makes detection process start again
    1: "'SETPARAMS 527=1;'",  # For OBD
    2: "'SETPARAMS 527=2;'",  # For J1939
    3: "'SETPARAMS 527=3;'",  # For mixed 2 and 4
    4: "'SETPARAMS 527=4;'",  # For J1708
    5: "'SETPARAMS 527=5;'",  # For AutoDetect
    6: "'SETPARAMS 527=6;'",  # For Second J1939**
    7: "'SETPARAMS 520=0;'",  # Turning off silent mode
    8: "'DIAG CAN'",         # Returns data on the device's canbus status
    9: "'DIAG ELD'",         # Minimum conformity of found engine data for ELD usage
    10: "'DIAG DISC'",        # Retrieves ECU data discovered
    11: "'DIAG NETWORK'",     # Retrieves data on the device's network
    12: "'DIAG QUEUE'",       # Returns information about the device's packet queue
    13: "'DIAG VERSION'",     # Returns information on the device's version
    14: "'DIAG CONFIG'",      # Retrieves information about the current configuration of a device
    15: "'DIAG DEVICEINFO'",  # Retrieves information about the device BLE
    16: "'SETPARAMS 994=124;'",  # odometer offset
    17: "'SETPARAMS 932=2;'",   # OBD odometer not overwrite GPS odometer
    18: "'RESET O 39254000'",   # Set desired GPS OD mult. by 1000
    19: "'RESET I 994680'",     # Set ELD EH mult by 3600
    20: "'RECAST'",             # Pushing config on cast
    21: "'BLETEST 9'",         # Reset BLE for 87/88 A,U,X,Z
    22: "'BLETEST 34'",        # Reset BLE for 87/88 B, C
    23: "'SETPARAMS 998=0;'"
}

eldr = '563o77hmgg6e7fszb2hzooh7qy'
xeld = 'pym4jckmfvje7gzlfu3ybwfuv4'
optima = 'vrendtlyjp7e5od7ivgfcsykce'
apis = [eldr, xeld, optima]
elds_in = []
command_in = []


def decode_vin(_vin):
    vehicle = VIN(_vin)
    make = vehicle.Make
    model = vehicle.Model
    year = vehicle.ModelYear
    return make, model, year


def get_input():
    while True:
        sn = input('Enter serial number or leave the field empty and press enter to finish: ')
        if sn == '':
            break
        elds_in.append(sn.strip(' '))
        vin_in = input('Enter vehicle VIN to decode: ')
        if vin_in != '':
            print(decode_vin(vin_in))
        comm = int(input(f'Enter the number of command (between 0 and 22) for {sn}: '))
        command_in.append(comm)
        while comm not in commands:
            print('Invalid input! Please try again')
            comm = int(input(f'Enter the number of command for {sn}: '))
            if comm in commands:
                command_in.append(comm)
                break


get_input()


def send_commands(_eld, _command_in):
    for api in apis:
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        purl = f'https://www.skyonics.net/api/skyonics/devicecommand?APIKey={api}&serialNumber={_eld}&mode=0'
        req = requests.post(purl, headers=headers, data=commands[_command_in])
        if req.status_code == 200:
            current_time = datetime.now().strftime('%H:%M:%S')
            if api == apis[0]:
                print(f'{current_time}  Sending command {commands[_command_in]} to {_eld} (ELD RIDER skyonics)')
            elif api == apis[1]:
                print(f'{current_time}  Sending command {commands[_command_in]} to {_eld} (XELD skyonics)')
            else:
                print(f'{current_time}  Sending command {commands[_command_in]} to {_eld} (OPTIMA skyonics)')
            if 1 <= _command_in <= 7:
                print(f'{current_time}  Wait 2 minutes before sending SHIPMODE to {_eld}')
                time.sleep(120)
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f'{current_time}  Sending SHIPMODE to {_eld}')
                requests.post(purl, headers=headers, data=commands[0])
                print(f'{current_time}  Wait 2 and a half minutes before sending DIAG CAN to {_eld}')
                time.sleep(180)
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f'{current_time}  Sending DIAG CAN to {_eld}')
                requests.post(purl, headers=headers, data=commands[8])
            break
        elif req.status_code != 200 and api == apis[2]:
            print(f'Oops, something went wrong. Status code {req.status_code}')
        else:
            continue


if __name__ == '__main__':

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(send_commands, elds_in, command_in)
