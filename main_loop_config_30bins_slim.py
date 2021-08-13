#!/usr/bin/python3

# main_loop_config_30bins.py
# version date: 02-22-2021
import serial
import time
import struct
import getopt
import math
import importlib.util
import sys
import subprocess
import os
import time
from datetime import datetime
#from periphery import GPIO
from gpiozero import LED
import asyncio
import socketio
import socket  # checking internet connection
import uuid
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
#import bluetooth
import json
import urllib3
import re


# Prevent warning for https/http
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVER_URL = 'http://192.168.1.130:8081'
INIT_URL = 'http://192.168.1.130:8081/init'
DATA_URL = 'http://192.168.1.130:8081/raw-data'
WS_URL = 'ws://192.168.1.130:8081'
CHECK_VERSION_URL = 'http://192.168.1.130:8081/mvp-check-update'
GET_VERSION_URL = 'http://192.168.1.130:8081/mvp-get-update'

JWT_PATH = '/home/root/jwt.txt'
VERSION_PATH = '/home/root/version.txt'

# Asyncio Init
loop = asyncio.get_event_loop()
# WebSocket Init
sioRemote = socketio.Client()




# Duration Time enumeration
fs = 100  # collection sampling rate
FOUR_HOUR = 14400*fs
THREE_HOUR = 10800*fs
TWO_HOUR = 7200*fs
ONE_HOUR = 3600*fs
TWENTY_MIN = 1200*fs
TEN_MIN = 600*fs
FIVE_MIN = 300*fs
TWO_MIN = 120*fs
ONE_MIN = 60*fs
MIN_DUMP = 1800*fs  # dump time in ms

# Radar Data Structure assignment
HEADER_STRUCT = struct.Struct("<4H8I")
TLV_HEADER_STRUCT = struct.Struct("<2I")
TARGET_OBJECT_RAW25 = struct.Struct("fI6h4H6h4H3h")
TARGET_OBJECT_MORE10BINS = struct.Struct("H20h3h")  # test 10-bins,6-1-20
TARGET_OBJECT_MORE30BINS = struct.Struct("H60h3h")  # test 30-bins,6-6-20
# default, change it below with CSV_VER!
TARGET_OBJECT_STRUCT = TARGET_OBJECT_MORE30BINS


# Data collection source data types, select the CSV_VER to use below, 2-10-20
COL25_HEADER = ('tiwrapph,ti_ind,pk1real,pk1imag,pk2real,pk2imag,pk3real,pk3imag,pk1loc,pk2loc,pk3loc,pksdet,' +
                'smpk1real,smpk1imag,smpk2real,smpk2imag,smpk3real,smpk3imag,smpk1loc,smpk2loc,smpk3loc,smpksdet,' +
                'ticpxloc,ticpxreal,ticpximag')  # traditional format
COL15_HEADER = ('tiwrapphfixed,ti_ind,pk1real,pk1imag,pk2real,pk2imag,pk3real,pk3imag,pk1loc,pk2loc,pk3loc,pksdet,' +
                'ticpxloc,ticpxreal,ticpximag')  # new more improved format 2-10-20
COL10BINS_HEADER = ('ti_ind,startind,pk1real,pk1imag,pk2real,pk2imag,pk3real,pk3imag,pk4real,pk4imag,pk5real,pk5imag,pk6real,pk6imag,' +
                    'pk7real,pk7imag,pk8real,pk8imag,pk9real,pk9imag,pk10real,pk10imag,ticpxloc,ticpxreal,ticpximag')  # morebins format 6-1-20
COL30BINS_HEADER = ('ti_ind,startind,pk1real,pk1imag,pk2real,pk2imag,pk3real,pk3imag,pk4real,pk4imag,pk5real,pk5imag,pk6real,pk6imag,' +
                    'pk7real,pk7imag,pk8real,pk8imag,pk9real,pk9imag,pk10real,pk10imag,pk11real,pk11imag,pk12real,pk12imag,pk13real,pk13imag,pk14real,pk14imag,' +
                    'pk15real,pk15imag,pk16real,pk16imag,pk17real,pk17imag,pk18real,pk18imag,pk19real,pk19imag,pk20real,pk20imag,' +
                    'pk21real,pk21imag,pk22real,pk22imag,pk23real,pk23imag,pk24real,pk24imag,pk25real,pk25imag,pk26real,pk26imag,' +
                    'pk27real,pk27imag,pk28real,pk28imag,pk29real,pk29imag,pk30real,pk30imag,ticpxloc,ticpxreal,ticpximag')  # morebins format 6-9-20

CSV_VER = 'MVP30BINS'  # ex. MVP10BINS,MVPRAW25,MVPRAW15, set it here ---------

COL_HEADER = ''  # default
BYTES_TO_READ = 128  # default
if CSV_VER == 'MVPRAW15':
    COL_HEADER = COL15_HEADER
    TARGET_OBJECT_STRUCT = TARGET_OBJECT_RAW25
    BYTES_TO_READ = 128
elif CSV_VER == 'MVPRAW25':
    COL_HEADER = COL25_HEADER
    TARGET_OBJECT_STRUCT = TARGET_OBJECT_RAW25
    BYTES_TO_READ = 128
elif CSV_VER == 'MVP10BINS':
    COL_HEADER = COL10BINS_HEADER
    TARGET_OBJECT_STRUCT = TARGET_OBJECT_MORE10BINS
    BYTES_TO_READ = 96
elif CSV_VER == 'MVP30BINS':
    COL_HEADER = COL30BINS_HEADER
    TARGET_OBJECT_STRUCT = TARGET_OBJECT_MORE30BINS
    BYTES_TO_READ = 192

# Control Flags
print_debugs = False
connect_flag = True  # True - run Digital Ocean server connect
# def:False; True - run local dump of csv for you can fill up NXP Flash 5-14-20
local_csv_flag = True
# def:True-delete all csv in board before saving another one 7-13-20, will work for <= 60 duration
delete_csv_flag = True
uart_error_check_flag = True  # True - will detect UART errors, 5-2-20
check_update_flag = False  # True(def)-will download latest Git code

# Start Helper Functions
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


def log_req(req):
    if print_debugs == True:
        printSubP(req)
# ------------------------------------------------------------------------------


def formatTime(t):
    tt = t / 100
    minutes = tt // 60 if tt > 60 else 0
    seconds = tt % 60 if tt > 60 else tt
    return '{0:.0f}min {1:.0f}sec'.format(minutes, seconds)
# ------------------------------------------------------------------------------


def getInetAddr():
    try:
        ifconfig = subprocess.getoutput("ifconfig")
        seperate = ifconfig.split('wlan0')[1]
        inet_addr = seperate.split('inet addr:')[
            1].split(' Bcast:')[0].rstrip()
        return inet_addr
    except:
        return '192.168.1.130'
# ------------------------------------------------------------------------------


def printSubP(message):
    try:
        prep_message = message.replace('(', "\\(").replace(')', "\\)")
        # print(message)
        # Display done this way to force Linux to show stdout if this script is run with rc.local (at MVP startup)
        # In rc.local, it is run as "python3 /home/root/main_loop_config.py > /home/root/main.log 2>&1 &"
        # To view the HR debug msg, use "tail -f main.log" to see the subprocess() output
        subprocess.call('echo {0}'.format(prep_message), shell=True)
    except:  # 7-24-20
        print('Error in printSubP() fcn')
# ------------------------------------------------------------------------------


def swap_4_byte_0xhex(hex_str):
    # pass a string of the form  '0x3412' and receive back a string of '0x1234'
    if len(hex_str) == 6:
        ret_val = hex_str[0]+hex_str[1]+hex_str[4] + \
            hex_str[5]+hex_str[2]+hex_str[3]
    else:
        ret_val = hex(0)
    return(ret_val)
# End Helper Functions
# ------------------------------------------------------------------------------


class RadarControl:
    def __init__(self):
        # WS
        self.sio = sioRemote
        self.local = False
        self.url = DATA_URL
        # Config
#        self.silent = True
        self.silent = False
        self.config_file_base = '/home/root/config_files/'
        # 'iwr_profile_BW1000M_fs100_shortdist0to60_060120.cfg' #jgi 6-1-20,testing
        self.config_file = 'iwr_profile_BW3000M_fs100_shortdist0to60_060120.cfg'

        self.cfg_port = '/dev/ttymxc2'
        self.data_port = '/dev/ttymxc3'
        self.run = False
        self.duration = TEN_MIN
        # Data Collection / Saving
        self.save = False
        self.will_send_data = True
        self.data_name = ''
        self.data_height_ft = 0
        self.data_height_in = 0
        self.data_weight = 0
        self.data_age_year = 0
        self.data_age_month = 0
        self.data_sleep_status = 'Awake'
        self.data_sex = 'Female'
        # UART
        self.prevticnt = 0  # 2-10-20
        self.uarterrorcount = 0  # 2-20-20
        self.prev_b = 0  # 2-20-20
        self.COMBOport = []
        self.COMBOconnected = False
        # Error processing 5-1-20
        self.uartShortErrCnt = 0
        self.uartLongErrCnt = 0
        self.uartShortErrThr = 10  # 10 is 0.1sec
        self.uartMaxErrThr = 70  # 70 is 0.7sec, ensure it's multiple of uartShortErrThr
        self.reset = LED(7)
#        self.sop1 = LED(1)  #MZ SOP[1] drive
#        self.sop1_2 = LED(25)  #MZ SOP[1 & 2] drive
        self.sop0 = LED(8)
        # Radar Reset
        # Toggle Reset Pin
        self.reset_radar()
        # Baby & Time Constant
        self.baby = False
        self.time_constant = False
        self.algo_version = '1.1'
        # Remote Data Processing
        self.remote_guess = 0
        self.remote_algo = True  # True - Giangi / False - Stan
        self.use_remote = False
        # Paolo Controls
        self.navg_jumps = 5
        self.jmp_th0 = 7
        self.jmp_th1 = 10
        self.no_breath_module = True
        self.no_breath_th = 5
        self.no_breath_sec_th = 3
        self.bin_res = 0.036058
        # Std / MoreBins 10bins, jgi 6-3-20
        # make this static setting control GUI (always def at 0!)
        self.radar_startind = 0
        # for std MVP25 profile, setting of 0 will start at col 2 to read the pks
        # for expt MVP10BINS profile, setting of x will start at col x+2 to read the pks.
        self.count = 0  # 7-23-20
        self.sioServerLagging = False  # tell us if server is lagging by too much
        # hold another event to happen in quickStopAndStart()
        self.quickStopAndStartHys = False
        self.currTime = 0
        self.prevTime = 0

    def reset_radar(self):
#        self.sop1.off()                  #MZ SOP[1] to low to ensure startup on little Franky#2
#        self.sop1_2.off()                #MZ SOP[1 & 2] to low to ensure startup on little Franky#2
        self.sop0.on()                   # Makes SOP[0] high
        printSubP("Asserting reset")
        self.reset.off()                 # Puts radar board to reset
        time.sleep(0.1)                  # Allow reset to take effect
        printSubP("Deasserting reset")
        self.reset.on()                  # Release radar from reset
        time.sleep(1)                    # Wait for radar firmware to be ready

    def init_port115k(self):
        if self.COMBOconnected and self.COMBOport.is_open:
            self.COMBOport.close()
            self.COMBOconnected = False
        try:
            self.COMBOport = serial.Serial('/dev/ttyS0', 115200, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=2, xonxoff=0, rtscts=0)   # open serial port
            self.COMBOconnected = True
            printSubP("UART opened at 115200")
            self.COMBOport.flushInput()
            self.COMBOport.flushOutput()
            time.sleep(1)
        except:
            printSubP("Error thrown in init_port115k() while initializing UART ports")

    def init_port921k(self):
        if self.COMBOconnected and self.COMBOport.is_open:
            self.COMBOport.close()
            self.COMBOconnected = False
        try:
            self.COMBOport = serial.Serial('/dev/ttyS0', 921600, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=2, xonxoff=0, rtscts=0)   # open serial port
            self.COMBOconnected = True
            printSubP("UART opened at 921600")
            time.sleep(1)
        except:
            printSubP("Error thrown in init_port921k() while initializing UART ports")

    def set_sio(self, sio):
        self.sio = sio
        self.get_status()

    def set_url(self, url):
        self.url = url
        self.get_status()

    def set_config(self, config):
        self.config_file = config
        self.get_status()

    def set_navg_jumps(self, n):
        self.navg_jumps = n
        self.get_status()

    def set_jmp_th0(self, n):
        self.jmp_th0 = n
        self.get_status()

    def set_jmp_th1(self, n):
        self.jmp_th1 = n
        self.get_status()

    def set_no_breath_module(self, n):
        self.no_breath_module = n
        self.get_status()

    def set_no_breath_th(self, n):
        self.no_breath_th = n
        self.get_status()

    def set_no_breath_sec_th(self, n):
        self.no_breath_sec_th = n
        self.get_status()

    def set_bin_res(self, n):
        self.bin_res = n
        self.get_status()

    def set_local(self, local):
        self.local = local
        self.get_status()

    def emit(self, evt, message):
        self.sio.emit(evt, message)

    def set_silent(self, silent):
        self.silent = silent
        self.get_status()

    def set_token(self, token):
        self.token = token

    def get_token(self):
        return self.token

    def set_duration(self, duration):
        self.duration = int(duration)
        self.get_status()

    def set_baby(self, baby):
        self.baby = baby
        self.get_status()

    def set_time_constant(self, time_constant):
        self.time_constant = time_constant
        self.get_status()

    def set_algo_version(self, algo_version):
        self.algo_version = int(algo_version)
        self.get_status()

    def set_will_send_data(self, will_send_data):
        self.will_send_data = will_send_data
        self.get_status()

    def pong(self, cnt):  # 7-23-20, back and forth heartbeat
        self.sio.emit('pong')  # back to server
        # if cnt%100 == 0:
        print('Got msg ', cnt)
        # is server lagging behind quite much?
        if (self.count - cnt) > 5000 and self.quickStopAndStartHys is False:
            self.sioServerLagging = True
            print('Server is overrun, mvp client will stop sending for short time...')

    def quickStopAndStart(self, waitTime):
        self.sioServerLagging = False  # reset flag
        self.quickStopAndStartHys = True  # hold another event to happen

        self.init_port_115k()

        # Restart uart ports to continue collection
        printSubP('Quick Stop/Start UART restarted quickly at ctr: {0}'.format(self.count))
        stopCmd = 'sensorStop\n'
        self.COMBOport.write(stopCmd.encode())
        time.sleep(0.10)

        time.sleep(waitTime)  # is this enough time for server to catch up?

        stry = "sensorStart\n"
        self.COMBOport.write(stry.encode('utf-8'))

        self.init_port921k()         # MZ

        self.quickStopAndStartHys = False

    def set_name(self, name):
        self.data_name = name

    def set_height_ft(self, ft):
        self.data_height_ft = ft

    def set_height_in(self, inches):
        self.data_height_in = inches

    def set_weight(self, weight):
        self.data_weight = weight

    def set_age_year(self, age_year):
        self.data_age_year = age_year

    def set_age_month(self, age_month):
        self.data_age_month = age_month

    def set_sleep_status(self, sleep_status):
        self.data_sleep_status = sleep_status

    def set_sex(self, sex):
        self.data_sex = sex

    def save_local(self, save):
        self.save = save
        self.get_status()

    def set_use_remote(self, use):
        self.use_remote = use
        self.get_status()

    def set_remote_guess(self, guess):
        self.remote_guess = guess
        self.get_status()

    def set_remote_algo(self, algo):
        self.remote_algo = algo
        self.get_status()

    def send_alert(self, alert):
        self.sio.emit('radar-alert-fb', {'message': alert})

    def send_version(self, version):
        self.sio.emit('software-version-fb', {'version': version})

    # Send status to AWS server
    def get_status(self):
        if connect_flag:
            self.sio.emit('radar-control-fb',
                          {'radar': self.run,
                           'duration': self.duration,
                              'silent': self.silent,
                              'config_file': self.config_file,
                              'cfg_port': self.cfg_port,
                              'data_port': self.data_port,
                              'baby': self.baby,
                              'time_constant': self.time_constant,
                              'algo_version': self.algo_version,
                              'will_send_data': self.will_send_data,
                              'data_name': self.data_name,
                              'data_height_ft': self.data_height_ft,
                              'data_height_in': self.data_height_in,
                              'data_weight': self.data_weight,
                              'data_age_year': self.data_age_year,
                           'data_age_month': self.data_age_month,
                              'data_sleep_status': self.data_sleep_status,
                              'data_sex': self.data_sex,
                              'remote_algo': self.remote_algo,
                              'remote_guess': self.remote_guess,
                              'use_remote': self.use_remote,
                              'navg_jumps': self.navg_jumps,
                              'jmp_th0': self.jmp_th0,
                              'jmp_th1': self.jmp_th1,
                              'no_breath_module': self.no_breath_module,
                              'no_breath_th': self.no_breath_th,
                              'no_breath_sec_th': self.no_breath_sec_th,
                              'bin_res': self.bin_res})

    # 6-3-20 Add timeStamp_end
    def send_data(self, data, CSV_VER, timeStamp, timeStamp_end, file_part):
        url = self.url
        data_path = ""

        # Find bw and fs from the config_file name, 7-28-20
        config_splits = self.config_file.split('_')
        bws = [x for x in config_splits if 'BW' in x][0][2:]
        fss = [x for x in config_splits if 'fs' in x][0][2:]

        # Add row header as metadata info for CSV file, 2-10-20
        _, MVP_name = get_nametxt()
        header_save_meta = COL_HEADER + ',bw=' + bws + ',fs=' + fss + ',' + MVP_name + ',uartcnt=' \
            + str(self.uartLongErrCnt) + ',Timestamp=' + str(timeStamp) + \
            ',End=' + str(timeStamp_end) + ',' + file_part
        data_append = header_save_meta + '\n' + data

        try:
            # delete old csv files except the last modified file, 7-13-20
            if delete_csv_flag:
                files = os.listdir()
                csv_files = list(filter(lambda f: f.endswith('.csv'), files))
                print('Deleting old csv files except the last modified file')
                csv_files_sorted = sorted(
                    csv_files, key=lambda t: os.stat(t).st_mtime)
                for x in csv_files_sorted[:-1]:
                    print('Deleting filename: ', x)
                    os.remove(x)

            # write to a .csv file, 5-14-20, 7-13-20 todo: make it same filename as in server
            save_name = '{0}_bw{1}_fs{2}_{3}_AGE_{4}_{5}_TIME_{6}_{7}.csv'.format(self.data_name,
                                                                                  bws, fss, CSV_VER, self.data_age_year, self.data_age_month, timeStamp, file_part)
            printSubP('Saving to csv file {0}'.format(save_name))
            data_path = '/home/root/{0}'.format(save_name)
            f = open(data_path, 'w')
            f.write(data_append)

        except Exception as e:
            printSubP('\n\nError:\n{0}'.format(e))
            printSubP("Except Block Hit under send_data module")
        finally:
            f.close()

        # send to subprocess (disabled)
        if False and os.path.exists(data_path):  # disable 5-14-20
            printSubP('POSTing data from {0}'.format(MVP_name))
            name_args = '{0} {1} {2} {3} {4} {5} {6} {7}'.format(self.data_name,
                                                                 self.data_height_ft,
                                                                 self.data_height_in,
                                                                 self.data_weight,
                                                                 self.data_age_year,
                                                                 self.data_age_month,
                                                                 self.data_sleep_status,
                                                                 self.data_sex)
            run_args = '{0} {1} {2} {3}'.format(
                name_args, file_part, CSV_VER, timeStamp)
            run_str = 'python3 /home/root/post_data_config.py {0} {1} {2} {3} &'.format(
                data_path, url, self.token, run_args)
            subprocess.run(run_str, shell=True)

    def read_aux_data(self, data, count):
        x = 0
        y = HEADER_STRUCT.size
        dataheader = data[x:y]
        b = HEADER_STRUCT.unpack(dataheader)
        frame_index = count
        TI_frame_index = b[7]

        x = y + TLV_HEADER_STRUCT.size
        y = x + TARGET_OBJECT_STRUCT.size
        dataAux = data[x:y]

        # print('TI_frame_index:',TI_frame_index,',prevticnt:',self.prevticnt)
        # 5-2-20 was False
        if uart_error_check_flag and ((count % 100 == 0) and (count > 30) and (TI_frame_index != (self.prevticnt + 1))):
            printSubP('TI_frame_index is not moving up by 100, possible UART corruption at ${0} - Restarting NXP board now. You need to start collection again'.format(count))
            self.prevticnt = TI_frame_index
            ArrayPeak = self.prev_b  # use the last good b here
            self.uarterrorcount = 1  # maintain uart error ctr, change to flag 7-22-20
            try:
                # Restart uart ports to continue collection
                printSubP('UART restarted quickly at ctr: {0}'.format(frame_index))
                # if self.data_port.checkStatus():
                self.init_port115k()
            except:
                # should not happen
                logging.debug('UART serial error thrown at uart.close() and open()')
            # raise Exception('Possible UART corruption') #2-20-20 #5-2-20

        else:
            ArrayPeak = list(TARGET_OBJECT_STRUCT.unpack(dataAux))
            # Save to previous value
            self.prevticnt = TI_frame_index
            self.prev_b = ArrayPeak

        if CSV_VER == 'MVPRAW15':
            # Form the 15-col format
            del ArrayPeak[12:22]
            # turn to fixed-pt multiplied by 1000
            ArrayPeak[0] = int(ArrayPeak[0] * 1000)
            ArrayPeak[1] = TI_frame_index

        elif CSV_VER == 'MVP10BINS':  # 6-1-20
            ArrayPeak.insert(0, TI_frame_index)

        elif CSV_VER == 'MVP30BINS':  # 6-6-20
            ArrayPeak.insert(0, TI_frame_index)

        else:
            printSubP("Invalid CSV_VER selected")
            raise Exception('Invalid CSV_VER selected')

        self.prevticnt = TI_frame_index  # save to prev TI cnt

        return ArrayPeak, TI_frame_index

    def read_sensor(self, run):
        self.uartShortErrCnt = 0  # reset error cnt on each Start btn press
        self.uartLongErrCnt = 0

        if not self.run:
            printSubP('Starting read_sensor with {0}'.format(run))
            self.run = run
            self.get_status()

            # self.set_duration(TWO_HOUR) #temporary if needed!
            # self.set_algo_version(80) #2-13-20, temp

            # Restart CLI UART here, assumed to be init already
            self.reset_radar()
            self.init_port115k()
#            if self.COMBOport.is_open is False:
#             if self.COMBOconnected is False:
#                 if self.COMBOport.is_open is False:
#                 printSubP("Opening CLI uart again")
# #                self.COMBOport.open()
#                 self.init_port115k()
#                 time.sleep(0.2)

            # self.COMBOport.flushInput()
            # self.COMBOport.flushOutput()
            # time.sleep(0.2)

            chosen_config = '{0}{1}'.format(
                self.config_file_base, self.config_file)
            config = [line.rstrip('\r\n') for line in open(chosen_config)]

#            self.init_port115k() #MZ

            printSubP("Writing Config To Radar")
            printSubP('-------------------------------------------')
            for i in config:
                printSubP(i)
                stry = i + '\n'
                self.COMBOport.write(stry.encode('utf-8'))

                # if not self.silent:  # not used for now
                #     # print(i)
                #     time.sleep(0.2)
                #     # read response from sensor
                #     bytesAvailable = self.COMBOport.inWaiting()
                #     CLIresponse = self.COMBOport.read(bytesAvailable)
                #     print(CLIresponse)
                time.sleep(0.3)  # time delay between cmds

            time.sleep(1)  # todo: need to validate this timing
            stry = "sensorStart\n"
            self.COMBOport.write(stry.encode('utf-8'))
            time.sleep(0.01)

            self.init_port921k()

            if True:  # try:
                printSubP("Waiting To Receive Data......")
                time.sleep(2)

                # Init counter
                self.count = 1  # loop ctr
                part_cnt = 1  # file part ctr

                dres = []
                dres_append = ""
                startTimeStamp = ""
                startTime = ""

                printSubP('Radar Running')
                printSubP('-------------------------------------------')
                if (self.count == 1):  # initial timestamp
                    startTimeStamp = '{0}'.format(
                        datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
                    startTime = datetime.now().timestamp()  # since epoch
                    printSubP("Radar received data started on: now {}".format(startTimeStamp))

                # cnt = 0
                while self.run:
                    try:
                        if self.sioServerLagging:
                            self.quickStopAndStart(5)
                        data = self.COMBOport.read(BYTES_TO_READ)
                        # cnt += 1
                        # if cnt > 100:
                        #     print("DT: " + data)
                        #     cnt = 0
                        if len(data) <= 0:
                            print("No data !!!")
                        else:
                            dres, ti_count = self.read_aux_data(data, self.count)
                    except Exception as e:
                        # 5-1-20
                        printSubP("------Except Block Hit in self.read_aux_data-------")

                    if self.uarterrorcount == 1:  # check error flag, 7-22-20
                        # auto restart NXP board and alert React app (todo: alert box to user)
                        if connect_flag:
                            self.sio.emit('radar-error-fb',
                                          {'error': 'uart error'})

                        # Manage our UART error logs and reboot scheme here 5-1-20
                        self.uarterrorcount = 0  # reset flag
                        self.uartShortErrCnt += 1
                        self.uartLongErrCnt += 1
                        printSubP("---Radar hit err short cnt:{} , long cnt:{}".format(
                            self.uartShortErrCnt, self.uartLongErrCnt))

                        if self.uartShortErrCnt == self.uartShortErrThr:
                            self.uartShortErrCnt = 0  # clear short cntr
                            printSubP(
                                "------Error: due to short err cnt-------")
                            # False, deactivate reboot for now
                            self.reboot(False)

                            if self.uartLongErrCnt == self.uartMaxErrThr:
                                printSubP(
                                    "------Error: will reboot now due to long err cnt-----")
                                self.reboot(False)  # True, will reboot

                    s = ",".join(str(x) for x in dres)
                    s += "\n"

                    # send to server - Stan/Giangi Algos, Graphs, Safe Save
                    self.sio.emit('radar-data-server-all-fb', {
                        'data': s,
                        'csv_ver': CSV_VER,
                        'duration': self.duration,
                        'will_send_data': self.will_send_data,
                        'count': self.count,
                        'data_name': self.data_name,
                        'data_height_ft': self.data_height_ft,
                        'data_height_in': self.data_height_in,
                        'data_weight': self.data_weight,
                        'data_age_year': self.data_age_year,
                        'data_age_month': self.data_age_month,
                        'data_sleep_status': self.data_sleep_status,
                        'data_sex': self.data_sex,
                        'timeStamp': startTimeStamp,
                        'stop': False,
                        'guess': self.remote_guess,
                        'year': self.data_age_year,
                        'month': self.data_age_month,
                        'baby': self.baby,
                        'time_constant': self.time_constant,
                        'navg_jumps': self.navg_jumps,
                        'jmp_th0': self.jmp_th0,
                        'jmp_th1': self.jmp_th1,
                        'no_breath_module': self.no_breath_module,
                        'no_breath_th': self.no_breath_th,
                        'no_breath_sec_th': self.no_breath_sec_th,
                        'bin_res': self.bin_res,
                        'config_file': self.config_file
                    })

                    # Display log to output
                    if (self.count % 100 == 0):
                        if self.count == 100:
                            self.prevTime = startTime
                            self.currTime = datetime.now().timestamp()  # in sec from epoch time, float
                        else:
                            self.prevTime = self.currTime
                            self.currTime = datetime.now().timestamp()

                        diffTimeStamp = self.currTime - self.prevTime
                        currTimeNow = datetime.now().strftime('%H-%M-%S')
                        printSubP('{0}, cnt {1}, ti {2}, Time {3} Delta {4:.2f}'.format(
                            formatTime(self.count), self.count, ti_count, currTimeNow, diffTimeStamp))

                    # Data Dump to device
                    if local_csv_flag:  # allows local csv save 5-14-20
                        dres_append += s  # this goes with local csv save
                        count = self.count

                        # 4hrs - 14400*100, 8 chunks - 8x 1800x100
                        if ((self.duration == FOUR_HOUR) and (count % MIN_DUMP == 0)):
                            printSubP('4hr Chunk (count = {0})'.format(count))
                            file_part = 'PART_{0}_8'.format(part_cnt)
                            part_cnt += 1
                            timeStamp_end = '{0}_'.format(
                                datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
                            self.send_data(dres_append, CSV_VER, startTimeStamp, timeStamp_end, file_part)
                            # refresh timestamp and dres_append
                            dres_append = ""
                            printSubP(
                                "Radar data timestamp on: now {0}".format(timeStamp_end))
                            if count == self.duration:  # stop radar process, jgi 2-3-20
                                printSubP(
                                    'Reached end of 4hr test at: {0}'.format(timeStamp_end))
                                self.stop_sensor()
                                break

                        # 3hrs - 10800*100, 6 chunks - 6x 1800*100
                        elif ((self.duration == THREE_HOUR) and (count % MIN_DUMP == 0)):
                            printSubP('3hr Chunk (count = {0})'.format(count))
                            file_part = 'PART_{0}_6'.format(part_cnt)
                            part_cnt += 1
                            timeStamp_end = '{0}_'.format(
                                datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
                            self.send_data(dres_append, CSV_VER, startTimeStamp, timeStamp_end, file_part)
                            # refresh timestamp and dres_append
                            dres_append = ""
                            printSubP(
                                "Radar data timestamp on: now {0}".format(timeStamp_end))
                            if count == self.duration:  # stop radar process
                                printSubP(
                                    'Reached end of 3hr test at: {0}'.format(timeStamp_end))
                                self.stop_sensor()
                                break

                        # 2hr - 7200*1100, 4 chunks - 4x 1800*100
                        elif ((self.duration == TWO_HOUR) and (count % MIN_DUMP == 0)):
                            printSubP('2hr Chunk (count = {0})'.format(count))
                            file_part = 'PART_{0}_4'.format(part_cnt)
                            part_cnt += 1
                            timeStamp_end = '{0}'.format(
                                datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
                            self.send_data(dres_append, CSV_VER, startTimeStamp, timeStamp_end, file_part)
                            # refresh timestamp and dres_append
                            dres_append = ""
                            printSubP(
                                "Radar data timestamp on: now {0}".format(timeStamp_end))
                            if count == self.duration:  # stop radar process
                                printSubP(
                                    'Reached end of 2hr test at: {0}'.format(timeStamp_end))
                                self.stop_sensor()
                                break

                        # 1hr and less, todo: check if 1hr can survive queiuing test
                        # save data once Stop is pressed on GUI, 7-22-20
                        elif (count % self.duration == 0 or self.run is False):
                            if True or self.will_send_data:  # will run for local save 5-14-20
                                file_part = ''  # nothing
                                timeStamp_end = '{0}'.format(
                                    datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
                                self.send_data(dres_append, CSV_VER, startTimeStamp, timeStamp_end, file_part)
                                dres_append = ""
                                printSubP(
                                    "Radar data timestamp on: now {0}".format(timeStamp_end))

                            # if self.save: #not used
                            #    save_name = '{0}_{1}_ID_TEMP_SAVE_AGE_{3}_{4}_TIME_{5}.csv'.format(self.data_name, CSV_VER, self.data_age_year, self.data_age_month, timeStamp)
                            #    with open(save_name, 'w') as f:
                            #        for line in dres_append:
                            #            f.write(line)
                            # refresh timestamp and dres_append
                            dres_append = ""

                    if count == self.duration or self.run is False:  # stop radar process
                        printSubP('Reached end of {0} min test that started on {1}'.format(
                            self.duration/fs/60, startTimeStamp))
                        self.stop_sensor()
                        break

                    self.count += 1  # loop ctr

                # Add row header (1st row) metadata on the remote server CSV file, 6-3-20,5-12-20
                _, MVP_name = get_nametxt()
                timeStamp_end = '{0}'.format(
                    datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
                printSubP('Sending header metadata from {0}'.format(MVP_name))
                header_meta = COL_HEADER + ',fs=' + str(fs) + ',' + MVP_name + ',uartcnt=' + str(
                    self.uartLongErrCnt) + ',Timestamp=' + str(startTimeStamp) + ',End=' + str(timeStamp_end)
                # print('header_meta:',header_meta)
                self.sio.emit('radar-data-server-all-fb', {
                    'data': header_meta,
                    'csv_ver': CSV_VER,
                    'duration': self.duration,
                    'will_send_data': self.will_send_data,
                    'count': self.count,
                    'data_name': self.data_name,
                    'data_height_ft': self.data_height_ft,
                    'data_height_in': self.data_height_in,
                    'data_weight': self.data_weight,
                    'data_age_year': self.data_age_year,
                    'data_age_month': self.data_age_month,
                    'data_sleep_status': self.data_sleep_status,
                    'data_sex': self.data_sex,
                    'timeStamp': startTimeStamp,
                    'stop': True,
                    'guess': self.remote_guess,
                    'year': self.data_age_year,
                    'month': self.data_age_month,
                    'baby': self.baby,
                    'time_constant': self.time_constant,
                    'navg_jumps': self.navg_jumps,
                    'jmp_th0': self.jmp_th0,
                    'jmp_th1': self.jmp_th1,
                    'no_breath_module': self.no_breath_module,
                    'no_breath_th': self.no_breath_th,
                    'no_breath_sec_th': self.no_breath_sec_th,
                    'bin_res': self.bin_res,
                    'config_file': self.config_file})

                # End of radar process
                # 5-2-20
                printSubP(
                    '-----------Total uartLongErrCnt: {} --------------'.format(self.uartLongErrCnt))
                printSubP('Profile used: {}'.format(self.config_file))
                printSubP('Reached end of radar process')

            '''
            except Exception as e:
                #printSubP('\n\nError:\n{0}'.format(e))
                printSubP("Except Block Hit under Radar module")
                if connect_flag:
                    self.sio.emit('radar-error-fb', { 'error': e })
                #self.reboot() #restart NXP board, remove 5-2-20
            except KeyboardInterrupt:
                pass
            finally: 
                self.stop_sensor()
            '''

    def stop_sensor(self, uart_restart=False):
        printSubP('stop_sensor() called')
        if self.run:
            stopCmd = 'sensorStop\n'
            self.COMBOport.write(stopCmd.encode())
            self.run = False  # todo:adam, tell React to enable Start btn
            time.sleep(1)  # 2-3-20
            self.get_status()  # todo, test 2-3-20
            self.sio.emit('remote-processing-graph-stop-cmd')
            self.sio.emit('remote-processing-dual-stop-cmd')
            if self.use_remote:
                self.sio.emit('remote-processing-stop-cmd')

        self.get_status()  # inform the GUI on status
#        if self.COMBOport.is_open:
#            self.COMBOport.close()  # close cmd uart
        time.sleep(0.2)

        # By default, we won't restart uart here unless if you pass True, jgi
        if uart_restart:
            #self.COMBOport.open()  # assuming port is close to begin with
            self.init_port115k()
            time.sleep(0.2)

        self.reset_radar()  # radar nrst pin toggle
        time.sleep(0.2)
        # self.init_ports() # open both uart
        printSubP("Exited Gracefully")

    def reboot(self, reboot_flag=True):
        if reboot_flag:  # 5-2-20 add way to deactivate all reboot in this script
            printSubP("Restarting NXP board for about 30sec now-----")
            self.stop_sensor()
            self.run = False  # 'reboot' # todo:adam, open React alert box telling user that reboot had happen, wait 30s, then enable Start btn again
            self.get_status()
            subprocess.getoutput("reboot")
# ------------------------------------------------------------------------------


class WifiControl:
    def __init__(self):
        # WS
        self.sio = sioRemote
        self.pwr = True
        self.ssid = 'none'
        self.pub_ip = ''  # 6-9-20
        self.local_ip = ''
        self.connected = False
        self.connect()

    def set_sio(self, sio):
        self.sio = sio
        self.get_status()

    def set_pwr(self, pwr):
        if pwr == False:
            self.power_down()
        else:
            self.connect()

    def connect(self):
        # find known network names

        # MZ commented all:
        # known = (subprocess.getoutput(
        #     "cat /etc/wpa_supplicant.conf | grep ssid")).split()
        # known_names = self.get_names(str(known))

        # # if wpa_supplicant names is not available, go to Wifi AP pairing process (Mik) 8-21-20
        # printSubP('Known networks: {0}'.format(known_names))
        # if len(known_names) == 0:
        #     print('No wpa_supplicant file is present, going to Wifi AP pairing process')
        #     # call ap pairing process which will restart mvp also -------

        # # find available network names
        # subprocess.getoutput("ifconfig wlan0 up")
        # avail = subprocess.getoutput("iwlist wlan0 scan | grep SSID")
        # avail_names = self.get_names(avail)
        # # see if we're already connected to a network
        # self.update_status()
        # self.pwr = True
        # # see if any known networks are available. If they are, connect to one
        # if (self.connected == False) & (len(set(known_names) & set(avail_names)) > 0):
        #     # this shouldn't actually run because wifi should start on boot
        #     subprocess.run("/usr/share/startup/startup_wifi")
        #     self.update_status()
        # # get public and local IPs, 6-9-20
        # self.local_ip = getInetAddr()
        # self.pub_ip = subprocess.getoutput("wget -qO - icanhazip.com")
        # printSubP('Local IP addr: {0}'.format(self.local_ip))
        # printSubP('Public IP addr: {0}'.format(self.pub_ip))
        self.connected = True

    def check_connection(self):
        return self.connected

    def update_status(self):
        # MZ commented all below:
        # wlan = subprocess.getoutput("iwconfig 2>&1 | grep wlan0")
        # network = self.get_names(wlan)
        # print('update_status net:', network)
        # if network == []:
        #     self.connected = False
        #     self.ssid = 'none'
        # else:
        #     self.connected = True
        #     # there will be two strings b/w quotes: SSID and Nickname. SSID is first
        #     self.ssid = network[0]
        # self.get_status()

        # printSubP('WiFi connected: {0}'.format(self.connected))
        # printSubP('WiFi network: {0}'.format(self.ssid))
        # MZ added
        self.connected = True

    def get_names(self, string):
        names = re.findall('"([^"]*)"', str(string))
        return(names)

    def get_status(self):
        self.sio.emit('wifi-status-fb', {'pwr': self.pwr,
                                         'SSID': self.ssid,
                                         'connected': self.connected,
                                         'ip': self.local_ip,
                                         'pub_ip': self.pub_ip})

    def add_new(self, network, password):
        cmd = 'wpa_passphrase "{0}" "{1}" >> /etc/wpa_supplicant.conf'.format(
            network, password)
        subprocess.getoutput(cmd)
        printSubP('Network: {0} Added'.format(network))

    def power_down(self):
        subprocess.getoutput("killall udhcpc")
        subprocess.getoutput("killall wpa_supplicant")
        self.pwr = False
# ------------------------------------------------------------------------------
# pylint: disable=function-redefined
# ------------------------------------------------------------------------------
# Begin Remote SIO
# ------------------------------------------------------------------------------
# [Commands]
@sioRemote.on('radar-control-cmd')
def on_message(cmd):
    printSubP('radar-control-cmd: {0}'.format(cmd))
    if 'radar' in cmd:
        if cmd['radar'] == True:
            RDRControl.read_sensor(True)
        elif cmd['radar'] == False:
            RDRControl.stop_sensor()
    elif 'config_file' in cmd:
        RDRControl.set_config(cmd['config_file'])
    elif 'silent' in cmd:
        RDRControl.set_silent(cmd['silent'])
    elif 'reboot' in cmd:
        if cmd['reboot'] == True:
            RDRControl.reboot()
    elif 'duration' in cmd:
        RDRControl.set_duration(cmd['duration'])
    elif 'baby' in cmd:
        RDRControl.set_baby(cmd['baby'])
    elif 'time_constant' in cmd:
        RDRControl.set_time_constant(cmd['time_constant'])
    elif 'algo_version' in cmd:
        RDRControl.set_algo_version(cmd['algo_version'])
    elif 'will_send_data' in cmd:
        RDRControl.set_will_send_data(cmd['will_send_data'])
    elif 'data_name_change' in cmd:
        RDRControl.set_name(cmd['data_name_change']['data_name'])
        RDRControl.set_height_ft(cmd['data_name_change']['data_height_ft'])
        RDRControl.set_height_in(cmd['data_name_change']['data_height_in'])
        RDRControl.set_weight(cmd['data_name_change']['data_weight'])
        RDRControl.set_age_year(cmd['data_name_change']['data_age_year'])
        RDRControl.set_age_month(cmd['data_name_change']['data_age_month'])
        RDRControl.set_sleep_status(
            cmd['data_name_change']['data_sleep_status'])
        RDRControl.set_sex(cmd['data_name_change']['data_sex'])
        RDRControl.get_status()
    elif 'navg_jumps' in cmd:
        RDRControl.set_navg_jumps(cmd['navg_jumps'])
    elif 'jmp_th0' in cmd:
        RDRControl.set_jmp_th0(cmd['jmp_th0'])
    elif 'jmp_th1' in cmd:
        RDRControl.set_jmp_th1(cmd['jmp_th1'])
    elif 'no_breath_module' in cmd:
        RDRControl.set_no_breath_module(cmd['no_breath_module'])
    elif 'no_breath_th' in cmd:
        RDRControl.set_no_breath_th(cmd['no_breath_th'])
    elif 'no_breath_sec_th' in cmd:
        RDRControl.set_no_breath_sec_th(cmd['no_breath_sec_th'])
    elif 'bin_res' in cmd:
        RDRControl.set_bin_res(cmd['bin_res'])
    elif 'use_remote' in cmd:
        # on / off
        RDRControl.set_use_remote(cmd['use_remote'])
    elif 'remote_guess' in cmd:
        # for Giangi Algo
        RDRControl.set_remote_guess(cmd['remote_guess'])
    elif 'remote_algo' in cmd:
        # True = Giangi / False - Stan
        RDRControl.set_remote_algo(cmd['remote_algo'])
# - - - - - - - - - - - -
@sioRemote.on('wifi-control-cmd')
def on_message(cmd):
    printSubP('wifi-control-cmd: {0}'.format(cmd))
    if 'pwr' in cmd:
        WFControl.set_pwr(cmd['pwr'])
    elif 'network' in cmd and 'password' in cmd:
        WFControl.add_new(cmd['network'], cmd['password'])
# ----------------------------------------------------------------
# [Requests]
@sioRemote.on('radar-status-req')
def on_message():
    RDRControl.get_status()
    log_req('radar-status-req')
# - - - - - - - - - - - -
@sioRemote.on('wifi-status-req')
def on_message():
    WFControl.get_status()
    log_req('wifi-status-req')
# - - - - - - - - - - - -
# End Remote SIO
# ------------------------------------------------------------------------------
# Set SIO in Classes


def set_all_sio(sio):
    RDRControl.set_sio(sio)
    WFControl.set_sio(sio)


# ------------------------------------------------------------------------------
fb_update_period_s = 0.5
# ------------------------------------------------------------------------------
# Make necessary bash scripts executable - before classes init
os.chmod('/home/root/FFT_data/file_transfer.py', 0o755)
# ------------------------------------------------------------------------------
# Init Classes
RDRControl = RadarControl()
WFControl = WifiControl()
time.sleep(5)
# ------------------------------------------------------------------------------


def is_online(hostname):
    try:
        host = socket.gethostbyname(hostname)
        s = socket.create_connection((host, 80))
        s.close()
        return True
    except:
        pass
    return False
# ------------------------------------------------------------------------------


def use_jwt():
    try:
        printSubP("Using JWT")
        f = open(JWT_PATH, "r")
        fl = f.readlines()
        token = fl[0]
        sioRemote.connect(WS_URL, headers={'token': token})
        set_all_sio(sioRemote)
        RDRControl.set_token(token)
        f.close()
        printSubP('Websockets Online [Saved JWT]')
    except Exception as e:
        # Will catch Keyboard Interrupt Event
        printSubP('use_jwt() Error:\n{0}'.format(e))
        os.remove(JWT_PATH)
        make_jwt()
# ------------------------------------------------------------------------------


def get_nametxt():
    name_path = '/home/root/name.txt'
    nl = []
    with open(name_path) as n:
        for line in n:
            nl.append(line.rstrip('\n').rstrip('\r'))
    typ = nl[0]
    nickname = nl[1]
    return typ, nickname
# ------------------------------------------------------------------------------


def make_jwt():
    printSubP('Making JWT')
    # Generate UUID
    typ, nickname = get_nametxt()  # 2-10-20
    device_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, nickname))
    # Prevent Server Spam
    session = requests.Session()
    retry = Retry(connect=5, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    # Request JWT
    r = session.post(url=INIT_URL, data={
                     'uuid': device_uuid, 'type': typ, 'nickname': nickname}, verify=False)
    token = json.loads(r.text)
    # Save JWT to file for reuse
    f = open(JWT_PATH, 'w')
    f.write(token['token'])
    f.close()
    try:
        sioRemote.connect(WS_URL, headers={'token': token['token']})
        set_all_sio(sioRemote)
        RDRControl.set_token(token['token'])
        printSubP('Websockets Online [New JWT]')
    except socketio.exceptions.ConnectionError as err:
        printSubP("make_jwt() ConnectionError: {0}".format(err))
# ------------------------------------------------------------------------------


def start_server():
    if connect_flag is True:
        printSubP('Starting Server')
        # check if wifi is connected
        isConnected = WFControl.check_connection()
        while not isConnected:
            printSubP('WiFi not connected - retrying')
            WFControl.connect()
            time.sleep(5)
            isConnected = WFControl.check_connection()
        printSubP('WiFi is connected')

        # Check for current JWT token
        if os.path.exists(JWT_PATH):
            try:
                use_jwt()
            except Exception as e:
                printSubP('Error JWT Read:{0}'.format(e))
                os.remove(JWT_PATH)
                make_jwt()
        else:
            make_jwt()

    run_module = True
    try:
        while run_module:

            time.sleep(fb_update_period_s)  # 0.5sec

    except Exception as e:
        # Will catch Keyboard Interrupt Event
        printSubP('Error:\n{0}'.format(e))
        line_num = sys.exc_info()[-1].tb_lineno
        error_type = type(e).__name__
        printSubP('Error on line: {0}\ntype: {1}\nerror: {2}'.format(
            line_num, error_type, e))
        printSubP("Except Block Hit Within Server module")
        if connect_flag:
            RDRControl.emit('radar-error-fb', {'error': e})
            RDRControl.reboot(False)  # 5-2-20, disable reboot now
    except KeyboardInterrupt:
        pass
    finally:
        time.sleep(1)  # so it wont coincide with Radar process
        printSubP("Calling stop_sensor() from start_server()")
        RDRControl.stop_sensor()
        run_module = False


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    loop.run_until_complete(start_server())
