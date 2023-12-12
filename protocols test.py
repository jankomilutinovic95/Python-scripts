import pyvin
import requests
import time
import concurrent.futures
from datetime import datetime
from pyvin import VIN
import mysql.connector
import sys

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
    22: "'BLETEST 34'"        # Reset BLE for 87/88 B, C
}

eldr = '563o77hmgg6e7fszb2hzooh7qy'
xeld = 'pym4jckmfvje7gzlfu3ybwfuv4'
optima = 'vrendtlyjp7e5od7ivgfcsykce'
elds_in = []
command_in = []


def decode_vin(_vin):
    try:
        vehicle = VIN(_vin, error_handling=pyvin.RAISE)
        make = vehicle.Make
        model = vehicle.Model
        year = vehicle.ModelYear
        return model, make, year
    except Exception as e:
        print(e)


def get_command_in():
    comm = int(input('Enter the command number (between 0 and 22): '))
    command_in.append(comm)
    while comm not in commands:
        print('Invalid input! Please try again')
        comm = int(input('Enter the command number (between 0 and 22): '))
        if comm in commands:
            command_in.append(comm)
            break


def get_vin():
    vin_in = input('Enter vehicle VIN to decode and send appropriate protocol: ')
    if vin_in != '':
        print(decode_vin(vin_in))
        if int(VIN(vin_in).ModelYear) >= 2016:
            command_in.append(2)
        else:
            command_in.append(4)
    return vin_in


def get_input_auto():
    while True:
        db_in = input('Enter app number. 1 for ELD RIDER, 2 for XELD, 3 for OPTIMA ELD: ')
        if db_in == '1':
            db = mysql.connector.connect(host='143.244.147.69', user='robot', passwd='cpRobot01', database='eld_rider')
            break
        elif db_in == '2':
            db = mysql.connector.connect(host='206.189.204.157', user='robot', passwd='cpRobot01', database='eld')
            break
        elif db_in == '3':
            db = mysql.connector.connect(host='68.183.132.234', user='robot', passwd='cpRobot01', database='eld')
            break
        elif db_in == '4':
            db = mysql.connector.connect(host='localhost', user='root', passwd='Zivko', database='testdatabase')
            break
        else:
            print('Invalid input, please try again!')

    cursor = db.cursor()
    sn = f"""SELECT e.serialNum
             FROM elds e
             JOIN vehicles v
                ON e.id = v.eld_id
             WHERE v.vin LIKE '{get_vin()}'"""
    cursor.execute(sn)
    result = cursor.fetchone()
    cursor.close()
    db.close()
    if result is None:
        print('No eld assigned on this vehicle')
    else:
        elds_in.append(result[0])
        print(f'Assigned device SN: {result[0]}')


def get_input_man():
    sn = input('Enter serial number: ')
    while ('87' not in sn[0:2] or '88' not in sn[0:2]) and len(sn) != 12:
        sn = input('Invalid input! Check device SN and try again: ')
        if ('87' in sn[0:2] or '88' in sn[0:2]) and len(sn) == 12:
            elds_in.append(sn.strip(' '))
            break
    elds_in.append(sn.strip(' '))
    vin_in = input('Enter vehicle VIN to decode or leave the field empty to continue: ')
    if vin_in != '':
        print(decode_vin(vin_in))
    while True:
        try:
            get_command_in()
            break
        except ValueError:
            print('Invalid input! Please try again.')
            continue


def send_commands(_eld, _command_in):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    purl = f'https://www.skyonics.net/api/skyonics/devicecommand?APIKey={eldr}&serialNumber={_eld}&mode=0'
    req = requests.post(purl, headers=headers, data=commands[_command_in])
    if req.status_code == 200:
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f'{current_time}  Sending command {commands[_command_in]} to {_eld} (ELD Rider skyonics)')
        if 1 <= _command_in <= 7:
            print(f'{current_time}  Wait 2 minutes before sending SHIPMODE to {_eld}')
            time.sleep(120)
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f'{current_time}  Sending SHIPMODE to {_eld}')
            req = requests.post(purl, headers=headers, data=commands[0])
            print(f'{current_time}  Wait 2 and a half minutes before sending DIAG CAN to {_eld}')
            time.sleep(180)
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f'{current_time}  Sending DIAG CAN to {_eld}')
            req = requests.post(purl, headers=headers, data=commands[8])
    else:
        purl = f'https://www.skyonics.net/api/skyonics/devicecommand?APIKey={xeld}&serialNumber={_eld}&mode=0'
        req = requests.post(purl, headers=headers, data=commands[_command_in])
        if req.status_code == 200:
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f'{current_time}  Sending command {commands[_command_in]} to {_eld} (XELD skyonics)')
            if 1 <= _command_in <= 7:
                print(f'{current_time}  Wait 2 minutes before sending SHIPMODE to {_eld}')
                time.sleep(120)
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f'{current_time}  Sending SHIPMODE to {_eld}')
                req = requests.post(purl, headers=headers, data=commands[0])
                print(f'{current_time}  Wait 2 and a half minutes before sending DIAG CAN to {_eld}')
                time.sleep(180)
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f'{current_time}  Sending DIAG CAN to {_eld}')
                req = requests.post(purl, headers=headers, data=commands[8])
        else:
            purl = f'https://www.skyonics.net/api/skyonics/devicecommand?APIKey={optima}&serialNumber={_eld}&mode=0'
            req = requests.post(purl, headers=headers, data=commands[_command_in])
            if req.status_code == 200:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f'{current_time}  Sending command {commands[_command_in]} to {_eld} (Optima skyonics)')
                if 1 <= _command_in <= 7:
                    print(f'{current_time}  Wait 2 minutes before sending SHIPMODE to {_eld}')
                    time.sleep(120)
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f'{current_time}  Sending SHIPMODE to {_eld}')
                    req = requests.post(purl, headers=headers, data=commands[0])
                    print(f'{current_time}  Wait 2 and a half minutes before sending DIAG CAN to {_eld}')
                    time.sleep(180)
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f'{current_time}  Sending DIAG CAN to {_eld}')
                    req = requests.post(purl, headers=headers, data=commands[8])
            else:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f'{current_time}  Oops something went wrong. Error {req.status_code}')


if __name__ == '__main__':
    args = list(sys.argv)

    if args[1] == 1:
        if len(sys.argv) < 2:
            print('Script needs at least 1 VIN to work on...')
            exit(1)
        else:
            for n in range(2, len(sys.argv)):
                elds_in.append(args[n])
    elif args[1] == 2:
        if len(sys.argv) > 2:
            for n in range(2, len(sys.argv)):
                elds_in.append(args[n])
        else:
            print('Script needs at least 1 VIN to work on...')
            exit(1)

    elds = []
    commands = []

    for eld in elds_in:
        x = eld.split()
        elds.append(x[0])
        commands.append(x[1])

    while True:
        a_or_m = input('Enter 1 for auto, 2 for man or leave the field empty to finish with input: ')
        if a_or_m == '':
            break
        elif a_or_m == str(1):
            get_input_auto()
        elif a_or_m == str(2):
            get_input_man()
        else:
            print('Invalid input! Please try again.')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(send_commands, elds_in, command_in)

