#!/usr/bin/env python3
import sys
import os
import time
import shutil
import datetime
import json
import csv
import logging
import socket
import xlrd
import pyvisa_py
import pyvisa
from RsInstrument import *
from RsInstrument.RsInstrument import RsInstrument, BinIntFormat
import numpy as np
import itertools
import pandas as pd
from operator import itemgetter
from ppadb.client import Client as AdbClient
from glob import glob
from ctf_json_data import CtfJsonData


# create a log
logger = logging.getLogger(__name__)
# output format
logger_format = "%(relativeCreated)8d %(levelname)-12s %(filename)-35s %(funcName)25s %(lineno)5s: %(message)s"
fsw_host = 0
fsw_socket_port = 0
# get a logging handle to the screen
sh = logging.StreamHandler()
# format the output
sh.setFormatter(logging.Formatter(logger_format))
logger.addHandler(sh)

# Making a directory For the Run
mydir = os.path.join('{0}\\Logs_folder\\'.format(os.getcwd().split('D')[0]), '{0}_{1}_{2}'.format(sys.argv[1], datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), sys.argv[4],os.getcwd().split('D')[0]))
os.makedirs(mydir)
mydir_d = mydir.replace('\\', '\\\\')
logger.debug("Result log folder created succesfully {0}".format(mydir_d))
# get a logging file handle
#Creating directory for results
dest = os.path.join('{0}\\Logs_folder\\'.format(os.getcwd().split('D')[0]), 'LTE_RX_{0}_{1}'.format(sys.argv[1], sys.argv[4]))
#os.makedir(dest)
dest_d = dest.replace('\\', '\\\\')
                    
logfilename = mydir_d.replace('.py', '').replace('.PY', '')
timestr_l = time.strftime("%Y%m%d-%H%M%S")
logfilename = logfilename + '{0}.log'.format(timestr_l)
fh = logging.FileHandler(logfilename, mode='w')
# format outout
fh.setFormatter(logging.Formatter(logger_format))
# add file handle to logger instance
logger.addHandler(fh)


total_bands = ['Band2', 'Band4', 'Band5', 'Band12', 'Band13', 'Band66']
# to pick min/max power input file from ctf command ine

if sys.argv[4] == 'max' or sys.argv[4] == 'MAX':
    power = 'Maxpowerinputfile.xlsx'
    logger.debug("TEST is based on 3gpp MAX power Value -23dbm")
elif sys.argv[4] == 'min' or sys.argv[4] == 'MIN':
    power = 'Minpowerinputfile.xlsx'
    logger.debug("TEST is based on 3gpp  min power Value -20dbm")
else:
    logger.debug(" Please check the command line argument  either MAX/max or MIN/min valid, Refer to Test Description")

#pick the min/max input file from current directory
inp_file = ("{1}\\{0}".format(power, os.getcwd()))
wb = xlrd.open_workbook(inp_file)
for i in total_bands:
    if i == sys.argv[1]:
        #sheet = wb.sheet_by_index(i)
        sheet = wb.sheet_by_name(sys.argv[1]) # band
    else:
        logger.debug(" not valid argument to select the input band sheet")
row_count = int(sys.argv[2]) # start variant
loop_rst = 1
while row_count < int(sys.argv[3]): # stop variant
    pos = 0
    ##Loop startes for
    #time.sleep(120)
    logger.debug(132*'_')

    TEST_BAND = int(sheet.cell_value(1, 0))


#for row_count in range(1, 4) :
    TEST_BW = sheet.cell_value(row_count, 1)
    TEST_FREQ_DL = float(sheet.cell_value(row_count, 2))
    TEST_RB = int(sheet.cell_value(row_count, 3))
    Start_RB = int(sheet.cell_value(row_count, 4))
    Power_level_TYPE = float(sheet.cell_value(row_count, 5))
    TEST_CH_TYPE = str(sheet.cell_value(row_count, 6))
    # "freq_start": [30000000, 150000, 30000000, var, var],
    freq_start_r1 = int(sheet.cell_value(row_count, 7))
    freq_start_r2 = int(sheet.cell_value(row_count, 9))


    freq_stop_r1 = int(sheet.cell_value(row_count, 8))
    freq_stop_r2 = int(sheet.cell_value(row_count, 10))


    freq_start = [freq_start_r1, freq_start_r2]
    freq_stop = [freq_stop_r1, freq_stop_r2]


    # set log level
    logger.setLevel(logging.DEBUG)
    logger.debug("Band: 	\t Bandwidth : (MHz) \t	DL Frequency:  (MHz)	\tRB Allocation: 	\t RB Start: 	\t float(Power Level)       \t Channel type")
    logger.debug(" {0}	 \t\t  :{1} (MHz) \t\t	: {2} (MHz)\t	\t\t: {3}	   \t\t\t : {4}	\t\t\t  {5}  ".format(TEST_BAND, TEST_BW, TEST_FREQ_DL, TEST_RB, Start_RB, Power_level_TYPE))
    logger.debug(132 * '_')
    # socket class
    class c_socket(object):

        def __init__(self, host, port, **kwargs):
            """ class Socket

                :param host: str, - CMW IP address or Host Name
                :param port: int, - CMW socket port - default 5025 for SCPI
                :param timeout: float = 3, - timeout in seconds
                :param termchar: str = '\n' -  Delimiter character

            Example:
                kwargs = {'timeout': 60, 'termchar': '\n'}
                mySocket = Socket('172.24.224.111', 5025)
            """
            # get a log instance from logging
            if 'logger' in kwargs:
                self._logger = logging.getlogger('logger')
            else:
                self._logger = logging.getLogger(__name__)

            # size of the incoming buffer 4096 bytes
            self._buffer_size = 4096
            # pompt decorator for the logging
            self._logindicator_write = '>>'
            self._logindicator_read = '<<'
            # boolean
            self.is_connected = False
            # connection type
            self.type = 'socket'
            # populate the class
            # host or ip address
            if 'host' in kwargs:
                self.host = kwargs['host']
            else:
                self.host = host

            # socket port
            if 'port' in kwargs:
                self.port = kwargs['port']
            else:
                self.port = port

            # timeout
            if 'timeout' in kwargs:
                self.__timeout = kwargs['timeout']
            else:
                self.__timeout = 6

            # incoming byte delimiter
            if 'termchar' in kwargs:
                self.termchar = kwargs['termchar']
            else:
                self.termchar = '\n'

            # socket instance
            self._sock = None
            self.ask = self.query

        def __del__(self):
            """ __del__ - Class destructor
            """

            if self._sock is not None:
                # close socket if instance is not None
                self._close()
            self._sock = None

        def close(self):
            """ _close() - Close socket connection
            """
            try:
                if self._sock is not None:
                    self._logger.debug('Close Socket Handle: {0}'.format(self._sock))
                    self._close()
                self.is_connected = False

            except Exception as Err:
                raise Err

        def connect(self):
            """ connect() - Attempt to open a socket connection
            """
            try:

                if self.is_connected:
                    self.close()
                    self._sock = None

                # get a socket instance
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # configure the socket interface
                self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                # set socket timeout
                self.timeout = self.__timeout

                self._write = self._sock.sendall
                self._read = self._sock.recv
                self._close = self._sock.close

                # attempt to connect - if no connection then assume running in debug mode so
                # SCPI commands can be logged
                self._logger.debug('Open SOCKET Connection @: {0}:{1:d}'.format(self.host, self.port))
                try:
                    self._debug_mode = False
                    self._sock.connect((self.host, self.port))
                    self.timeout = self.__timeout

                except:
                    self._logger.error("SCPI Connection failed - run debug mode only ")
                    self._debug_mode = True

            except socket.error as Err:
                raise

            except Exception as Err:
                msg = 'Could not connect to host {0}:{1}'.format(self.host, self.port)
                self._logger.exception(msg)
                raise ValueError(msg)

            self.is_connected = True
            self._logger.debug(
                'SOCKET Connection Successfully Open with: {0}:{1} - SOCKET Handle: {2}'.format(self.host, self.port,
                                                                                                [self._sock]))

        def _check_connection(self):
            """ _check_connection() - Check socket connection

                :return: bool
            """
            if not self.is_connected:
                msg = 'Not connected!'
                self._logger.exception(msg)
                raise ValueError(msg)

        def _reconnect(self):
            """ _reconnect() - Re-connect a socket connection
            """
            self.close()
            self.connect()

        def write(self, scpi_cmd):
            """ write(scpi_cmd) - send SCPI command to socket interface

                :param scpi_cmd:

            """
            try:
                self._check_connection()

                self._logger.debug('{0}:{1} >> {2}'.format(self.host, self.port, scpi_cmd))

                command = (scpi_cmd + self.termchar).encode()
                self._sock.sendall(command)

            except Exception as Err:
                raise Err

        def read(self):
            """ read() - read incoming bytes from socket interface

                :return:  str
            """
            try:

                buffin = ''

                if self._debug_mode:
                    return ['']

                start = time.time()
                while True:

                    response = b''
                    self._check_connection()

                    response = self._sock.recv(4096)
                    buffin = buffin + response.decode()

                    if self.termchar in buffin:
                        buffin = buffin.replace(self.termchar, '')
                        break

                    if time.time() - start > self.timeout:
                        self._logger.warning('Timeout while reading socket.')
                        return ''

                if (buffin[0] == '"' and buffin[-1] == '"') or (buffin[0] == '"' and buffin[-1] == '"' and ';' in buffin):
                    buffout = [buffin]
                elif ',' in buffin:
                    buffout = buffin.split(',')
                else:
                    buffout = [buffin]

                self._logger.debug('{0}:{1} << [{2}]'.format(self.host, self.port, ','.join(buffout)))

                return buffout

            except Exception as Err:
                raise Err

        def _read_until(self):
            """ _read_until(()

                :return: response_byte - str byte
            """

            response_byte = b''
            start = time.time()
            while time.time() - start < self.timeout:

                try:
                    # read bytes from socket -  default buffer size 4096 bytes
                    response_temp = self._read(self._buffer_size)
                except:
                    self._logger.warning('Timeout while reading socket.')
                    self._reconnect()
                    return response_byte

                # add read bytes to the response
                response_byte += response_temp
                if self.termchar.encode('utf-8') in response_byte:
                    # exit if delimiter char found in the response_byte
                    return response_byte[:-1]

            self._logger.warning('Timeout waiting on termchar.')
            self._reconnect()
            return response_byte

        def query(self, command):
            """ query(command):  Send a SCPI command and retrieve the answer

                :param command: - str
                :return:  str
            """

            self._check_connection()
            self.write(command)
            response = ['']
            if '?' in command:
                response = self.read()
            return response

        # property timeout
        def __set_timeout(self, timeout_s):

            if timeout_s != self.__timeout:
                self.__timeout = timeout_s

            if self._sock is not None:
                self._sock.settimeout(self.__timeout)

        def __get_timeout(self):

            if self._sock is not None:
                self.__timeout = self._sock.gettimeout()
            if self.__timeout is None:
                self.__timeout = 6
            return self.__timeout

        timeout = property(__get_timeout, __set_timeout, None, """ timeout """)


    class c_lte(object):

        def __init__(self):
            self.sua = 1
            self.rf_port = "RF1C"
            self.converter = 1
            self.ul_att = 25.0
            self.dl_att = 25.0
            #self.imsi = '310260123456789'
            #self.band = 4
            #self.bw = 5

            #self.nrb = 50
            #self.tx_close_loop_power = 0.0
            #self.rs_epre = -85.0
            #self.apn = 'fast.t-mobile.com'
            self.qci = 5
            self.rb_d = {1.4: 6, 3: 15, 5: 25, 10: 50, 15: 75, 20: 100}
            self.bw_d = {2: [1.4, 3, 5, 10, 15, 20],
                         4: [1.4, 3, 5, 10, 15, 20],
                         5: [1.4, 3, 5, 10],
                         12: [1.4, 3, 5, 10],
                         13: [5, 10],
                         66: [1.4, 5, 20], }
            self.band_d = {2: [600, 600, 1930.0, 80.0],
                           4: [1950, 450, 2110.0, 400.0],
                           5: [2400, 250, 869.0, 45.0],
                           12: [5010, 170, 729.0, 30.0],
                           13: [5180, 100, 746.0, -31.0],
                           66: [66436, 700, 2110, 400]
                           }
            self.low_prb = 0
            self.rb_max = {1.4: 5, 5: 24, 10: 49, 20: 99}
            self.suw = 1
            self.suu = 1
            self.sua = 1
            self.rf_port = "RF1C"
            self.converter = 1
            #self.ul_att = 0.0
            #self.dl_att = 0.0
            #self.imsi = '0010010123456063'
            self.opc_key = "00000000000000000000000000000000"
            self.secret_key = "000102030405060708090A0B0C0D0E0F"
            self.milenage = False
            self.band = TEST_BAND
            self.tx_close_loop_power = Power_level_TYPE
            if TEST_CH_TYPE == 'low' or TEST_CH_TYPE == 'mid' or TEST_CH_TYPE == 'high' :
                self.chanel_type = TEST_CH_TYPE
                #logger.debug(self.chanel_type)
            else :
                logger.debug("CHOOSE the low or mid or high ")
            # Calculating the channel values:
            if self.chanel_type == 'low':
                self.dl_chan = int(self.band_d[self.band][0] + int(10 * TEST_BW / 2))
            elif self.chanel_type == 'mid':
                self.dl_chan = int((self.band_d[self.band][0] + (self.band_d[self.band][0] + self.band_d[self.band][1])) / 2)
            elif self.chanel_type == 'high':
                self.dl_chan = int(self.band_d[self.band][0] + self.band_d[self.band][1] - int(10 * TEST_BW / 2))

            self.ul_chan = int(self.dl_chan + 18000)
            self.dl_freq = TEST_FREQ_DL
            self.duplex_freq = self.band_d[self.band][-1]
            self.ul_freq = self.dl_freq - self.duplex_freq
            #self.rs_epre = -85.0
            #self.dl_total_power = -57.2
            logger.debug('print band: {0}'.format(self.band))
            #logger.debug('print channel value: {0}'.format(self.dl_chan))
            #logger.debug('print dl freq value: {0}'.format(self.dl_freq))
            #logger.debug('print power level: {0}'.format(self.tx_close_loop_power))


    dl_channel = c_lte().dl_chan
    logger.debug(dl_channel)
    rb = c_lte().rb_d.values()
    tx_close_loop_target_power = c_lte().tx_close_loop_power
    srb = c_lte().rb_max.values()
    logger.debug(list(srb))

    # Look for UE device
    # TODO: make CLI argument
    dut_adb_serial_number = '225c2b92'

    # Default is "127.0.0.1" and 5037
    client = AdbClient(host="127.0.0.1", port=5037)
    logger.info('version of module : %d', client.version())

    # get list of devices
    devices = client.devices()

    device_found = False
    for dev in devices:
        logger.info('detected : %s', dev.serial)
        if dev.serial == dut_adb_serial_number:
            device_found = True
            break

    if not device_found:
        logger.error('could not find %s. terminating script', dut_adb_serial_number)
        sys.exit(0)

    # connect to selected device
    device = client.device(dut_adb_serial_number)
    logger.info('connected to adb device %s', dut_adb_serial_number)

    # CMW instance
    cmw = None
    cmw_host = '127.0.0.1'
    cmw_socket_port = 5025
    cmw_socket_timeout = 6
    cmw_socket_termchar = '\n'
    fsw_socket_timeout = 6
    fsw_socket_termchar = '\n'

    DAU_PRESENT = True
    IMS_FLAG = True

    REGISTER_TIMEOUT = 60

    dau_service_l = ['DNS', 'FTP', 'HTTP', 'IMS2', 'EPDG']

    lte = c_lte()

    epdg_ip_v4 = "192.168.1.201"
    epdg_ip_v6 = "fc01::1"
    dau_ipv4_config = 'internal'
    dau_ipv6_config = 'internal'

    try:

        # read json file
        data = None
        f_json = os.path.curdir + os.sep + 'config_Rx.json'
        # fsw_json = os.path.curdir + os.sep + 'config.json'
        if os.path.exists(f_json):
            with open(f_json) as json_file:
                data = json.load(json_file)

            if 'cmw' in data:
                if 'host' in data['cmw']:
                    cmw_host = data['cmw']['host']

                if 'socket_port' in data['cmw']:
                    cmw_socket_port = data['cmw']['socket_port']

                if 'socket_timeout' in data['cmw']:
                    cmw_socket_timeout = data['cmw']['socket_timeout']

                if 'socket_termchar' in data['cmw']:
                    cmw_socket_termchar = data['cmw']['socket_termchar']

            if 'fsw' in data:
                if 'host' in data['fsw']:
                    fsw_host = data['fsw']['host']

                if 'socket_port' in data['fsw']:
                    fsw_socket_port = data['fsw']['socket_port']

                if 'socket_timeout' in data['fsw']:
                    fsw_socket_timeout = data['fsw']['socket_timeout']

                if 'socket_termchar' in data['fsw']:
                    fsw_socket_termchar = data['fsw']['socket_termchar']
            """
            if fsw_param' in data :
                rbw_value = data['fsw_param']['rbw'] # [ 1, 10 ,20 ,30 ]
                logger.
            """
            # Reading FSw spurious msmt settings from config.json
            if 'fsw_params' in data:
                if 'sweep_points' in data['fsw_params']:
                    sweep_point_value = data['fsw_params']['sweep_points'] # [ 800, 5000, 3300, 34000 ]
                if 'ranges' in data['fsw_params']:
                    range_num = data['fsw_params']['ranges'] # [ 800, 5000, 3300, 34000 ]
                if 'ref_lev' in data['fsw_params']:
                    ref_lev = data['fsw_params']['ref_lev']
                if 'att_rf' in data['fsw_params']:
                    att_rf = data['fsw_params']['att_rf']
                if 'transducer' in data['fsw_params']:
                    transducer = data['fsw_params']['transducer']
                """
                if 'freq_start' in data['fsw_params']:
                    freq_start = data['fsw_params']['freq_start']
                if 'freq_stop' in data['fsw_params']:
                    freq_stop = data['fsw_params']['freq_stop']
                """
                if 'rbw_in' in data['fsw_params']:
                    rbw_in = data['fsw_params']['rbw_in']
                if 'vbw_in' in data['fsw_params']:
                    vbw_in = data['fsw_params']['vbw_in']
                if 'detector_type' in data['fsw_params']:
                    detector_type = data['fsw_params']['detector_type']
                if 'limit' in data['fsw_params']:
                    limit = data['fsw_params']['limit']
                if 'sweep_time' in data['fsw_params']:
                    sweep_time = data['fsw_params']['sweep_time']

            if 'lte' in data:

                if 'sua' in data['lte']:
                    lte.sua = data['lte']['sua']

                if 'rf_port' in data['lte']:
                    lte.rf_port = data['lte']['rf_port']

                if 'converter' in data['lte']:
                    lte.converter = data['lte']['converter']

                if 'dl_att' in data['lte']:
                    lte.dl_att = data['lte']['dl_att']

                if 'ul_att' in data['lte']:
                    lte.dl_att = data['lte']['ul_att']
                logger.debug(132 * '_')
                if 'band' in data['lte']:
                    lte.band = data['lte']['band']

                if 'bw' in data['lte']:
                    lte.bw = data['lte']['bw']

                if 'rs_epre' in data['lte']:
                    lte.rs_epre = data['lte']['rs_epre']

                if 'imsi' in data['lte']:
                    lte.imsi = data['lte']['imsi']

                if 'apn' in data['lte']:
                    lte.apn = data['lte']['apn']

                if 'qci' in data['lte']:
                    lte.qci = data['lte']['qci']


        MCC = lte.imsi[0:3]
        MNC = lte.imsi[3:6]
        IMSI = lte.imsi[6:]
        SIM = 'TMO'

        # get argument parsed
        if '--cmw' in sys.argv:
            cmw_host = sys.argv[sys.argv.index("--cmw") + 1]

        if '--lte_band' in sys.argv:
            logger.debug(" inside sys arg")
            TEST_BAND = int(sys.argv[sys.argv.index("--lte_band") + 1])
            logger.debug(TEST_BAND)

        if '--lte_bw' in sys.argv:
             TEST_BW = float(sys.argv[sys.argv.index("--lte_bw") + 1])

        if '--lte_dl_chan' in sys.argv:
            dl_channel = int(sys.argv[sys.argv.index("--dl_channel") + 1])

        if '--lte_tx_close_loop_power' in sys.argv:
            tx_close_loop_target_power = float(sys.argv[sys.argv.index("--tx_close_loop_target_power") + 1])

        if '--dau_ipv4_external' in sys.argv:
            dau_ipv4_config = 'external'

        if '--dau_ipv6_external' in sys.argv:
            dau_ipv6_config = 'external'


        logger.info('{0}'.format(132 * '-'))
        logger.info('***** Script Setup CMW for LTE VoLTE/IMS call *****')
        logger.info('{0:<20} : {1}'.format('Date', time.asctime()))
        logger.info('{0:<20} : {1}'.format('Computer', socket.gethostname().upper()))
        logger.info('{0:<20} : {1}'.format('Operating System', os.name.upper()))
        logger.info('{0:<20} : {1}'.format('Target OS', sys.platform.upper()))
        logger.info('{0:<20} : {1}'.format('Python Version', sys.version.upper()))
        logger.info('{0:<20} : {1}'.format('Python Script', sys.argv[0]))
        logger.info('{0}'.format(132 * '-'))

        logger.info('{0}'.format(132 * '-'))
        logger.info('Get working directory')
        workdir = os.getcwd()
        logger.info('{0}'.format(workdir))
        logger.info('{0}'.format(132 * '-'))
        time.sleep(10)
        # Init CMW
        if 1:
            logger.info('{0}'.format(132 * '-'))
            logger.info('Create a Socket Class object to remote the CMW')
            kwargs = {'timeout': cmw_socket_timeout, 'temchar': cmw_socket_termchar}

            # get a socket instance for controlling CMW
            cmw = c_socket(cmw_host, cmw_socket_port, **kwargs)

            # connect to CMW
            cmw.connect()

            # set CMW display
            logger.info('{0}'.format(132 * '-'))

            # cmw.write("CALL:LTE:SIGN:PSWitched:ACTion DETach")
            # time.sleep(5)
            cmw.write('SYST:DISP:UPD ON')

            #if loop_rst == 1:
            logger.info('{0}'.format(132 * '-'))
            logger.info('RESET CMW')
            cmw.timeout = 1080.0
            cmw.write("*CLS")
            cmw.write("SYST:PRES:ALL")
            cmw.ask("*OPC?")
            #cmw.timeout = 10.0

            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('QUERY ID')

            if not hasattr(cmw, 'id'):
                setattr(cmw, 'id', 'CMW')
            if not hasattr(cmw, 'sn'):
                setattr(cmw, 'sn', '000000')
            if not hasattr(cmw, 'BASE_FW'):
                setattr(cmw, 'BASE_FW', 'CMW')

            buffin = cmw.ask("*IDN?")
            logger.debug(buffin)
            if 'k50' in buffin[2]:
                cmw.id = 'CMW500'
            elif 'k55' in buffin[2]:
                cmw.id = 'CMWC'
            elif 'k29' in buffin[2]:
                cmw.id = 'CMW290'

            # get serial number
            cmw.sn = buffin[2].split('/')[1]

            # Get BASE FW revision
            cmw.BASE_FW = buffin[3]

            # get cmw options
            logger.info('{0}'.format(132 * '-'))
            logger.info('QUERY CMW Option')
            if not hasattr(cmw, 'opt'):
                setattr(cmw, 'opt', [])
            cmw.opt = cmw.ask("*OPT?")

            if not hasattr(cmw, 'hw_list'):
                setattr(cmw, 'hw_list', [])
            cmw.hw_list = cmw.ask('SYST:BASE:OPT:LIST? HWOP,FUNC')[0][1:-1].split(',')

            if not hasattr(cmw, 'sw_list'):
                setattr(cmw, 'sw_list', [])
            cmw.sw_list = cmw.ask('SYST:BASE:OPT:LIST? SWOP,VALid')[0][1:-1].split(',')

            # get CMW LTE FW revision
            logger.info('{0}'.format(132 * '-'))
            logger.info('QUERY LTE FW Revision')
            if not hasattr(cmw, 'lte_sign_fw'):
                setattr(cmw, 'lte_sign_fw', [])
            cmw.lte_sign_fw = cmw.ask("SYST:OPT:VERS? \"CMW_LTE_Sig\"")[0][1:-1]

            if not hasattr(cmw, 'lte_mev_fw'):
                setattr(cmw, 'lte_mev_fw', [])
            cmw.lte_mev_fw = cmw.ask("SYST:OPT:VERS? \"CMW_LTE_Meas\"")[0][1:-1]

            # Check presence of DAU
            logger.info('{0}'.format(132 * '-'))
            if cmw.hw_list.count("H450A") != 0 or cmw.hw_list.count("H450B") != 0 or cmw.hw_list.count("H450D") != 0 or cmw.hw_list.count("H450H") != 0 or cmw.hw_list.count("H450I") != 0:
                DAU_PRESENT = True

            else:
                DAU_PRESENT = False
                logger.debug('Error: VoLTE call requires DAU option CMW-B450 ')
                raise ValueError('VoLTE call requires DAU option CMW-B450')

            logger.info('{0}'.format(132 * '-'))

            erreur = cmw.ask("SYST:ERR:ALL?")
            if erreur[0] != '0':
                raise ValueError(erreur)
            # End Init CMW
            # Configure CMW LTE CELL CMW DAU IMS2 server and VoLTE subscriber
            if 1:

                logger.info('{0}'.format(132 * '-'))
                logger.info('LTE Cell - TURN LTE CELL OFF')
                buffin = cmw.ask("SYST:SIGNaling:ALL:OFF;*OPC?")

                TIMEOUT = 120.0
                tstart = time.time()
                buffin = cmw.ask("SOUR:LTE:SIGN:CELL:STAT:ALL?")
                while not (buffin[0] == "OFF" and buffin[1] == "ADJ"):

                    # wait 500 ms
                    time.sleep(0.5)

                    # query LTE CELL state
                    buffin = cmw.ask("SOURce:LTE:SIGN:CELL:STAT:ALL?")

                    # check TIMEOUT
                    if (time.time() - tstart) > TIMEOUT:
                        # x = win32api.MessageBox(0, "TIMEOUT occurs")
                        raise ValueError('TIMEOUT - LTE Signaling Turn OFF')
                #
                logger.info('LTE Cell - LTE CELL IS TURN OFF')
                logger.info('{0}'.format(132 * '-'))

            # Configure DAU
            if DAU_PRESENT:

                logger.info('{0}'.format(132 * '-'))
                logger.info('DAU Configure Services')

                for service in dau_service_l:

                    # Check DAU service
                    status = cmw.ask("SOURce:DATA:CONT:{0}:STATe?".format(service))[0]

                    # Turn OFF
                    if status != 'OFF':
                        cmw.write("SOURce:DATA:CONT:{0}:STATe OFF".format(service))

                        status = ''
                        while status != 'OFF':
                            time.sleep(0.150)
                            status = cmw.ask("SOURce:DATA:CONT:{0}:STATe?".format(service))[0]

                        logger.debug('DAU service {0} is OFF'.format(service))

                # get IPV4 and IPV6 type
                buffipv4 = cmw.ask("CONFigure:DATA:CONTrol:IPVFour:ADDRess:TYPE?")[0]
                buffipv6 = cmw.ask("CONFigure:DATA:CONTrol:IPVSix:ADDRess:TYPE?")[0]

                if 'external' in dau_ipv4_config or 'external' in dau_ipv6_config:

                    logger.debug('DAU -  Configure IP COnfig to External Network')

                    if ('external' in dau_ipv4_config and not 'DHCPv4' in buffipv4) or (
                            'external' in dau_ipv6_config and 'ACONf' not in buffipv6):
                        logger.debug('DAU -  Turn OFF DAU')

                        # turn DAU OFF
                        cmw.write("SOURce:DATA:CONTrol:STATe OFF")

                        status = ''
                        while status != 'OFF':
                            time.sleep(1.0)

                            status = cmw.ask("SOURce:DATA:CONTrol:STATe?")[0]

                    if 'external' in dau_ipv4_config and 'DHCPv4' not in buffipv4:
                        logger.debug('DAU -  Set IP Config IPV4 to DHCP')
                        cmw.ask("CONFigure:DATA:CONTrol:IPVFour:ADDRess:TYPE DHCPv4;*OPC?")

                    if 'external' in dau_ipv6_config and 'ACONf' not in buffipv6:
                        logger.debug('DAU -  Set IP Config IPV6 to DHCP')
                        cmw.ask("CONFigure:DATA:CONTrol:IPVSix:ADDRess:TYPE ACON;*OPC?")

                    # turn DAU ON
                    status = cmw.ask("SOURce:DATA:CONTrol:STATe?")[0]
                    if 'ON' not in status:

                        logger.debug('DAU -  Turn ON DAU')
                        cmw.write("SOURce:DATA:CONTrol:STATe ON")

                        status = ''
                        while status != 'ON':
                            time.sleep(1.0)
                            status = cmw.ask("SOURce:DATA:CONTrol:STATe?")[0]

                    logger.debug('DAU -  Check DAU IPConfig')

                    buffin = cmw.ask("SENSe:DATA:CONTrol:LAN:DAU:STATus?")[0]
                    if "CONN" not in buffin:
                        raise ValueError("DAU Not connected to external Ethernet Network.")

                else:

                    logger.debug('DAU -  Check  IP Config  Network')

                    buffin = cmw.ask("CONFigure:DATA:CONTrol:IPVFour:ADDRess:TYPE?")[0]
                    if buffin != "AUT":
                        cmw.ask("CONFigure:DATA:CONTrol:IPVFour:ADDRess:TYPE AUT;*OPC?")

                    buffin = cmw.ask("CONFigure:DATA:CONTrol:IPVSix:ADDRess:TYPE?")[0]
                    if buffin != "AUTO":
                        cmw.ask("CONFigure:DATA:CONTrol:IPVSix:ADDRess:TYPE AUTO;*OPC?")

                # DAU -  Configure DNS Service
                logger.debug('DAU -  Configure DNS Service')
                cmw.write(
                        'CONFigure:DATA:CONT:DNS:LOCal:ADD "epdg.epc.mnc{0}.mcc{1}.pub.3gppnetwork.org", "{2}"'.format(MNC, MCC,
                                                                                                                       epdg_ip_v4))
                cmw.write(
                        'CONFigure:DATA:CONT:DNS:LOCal:ADD "epdg.epc.mnc{0}.mcc{1}.pub.3gppnetwork.org", "{2}"'.format(MNC, MCC,
                                                                                                                       epdg_ip_v6))

                # DAU IMS2 - Configure subscriber
                logger.debug('DAU IMS2 - Configure subscriber')
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:PRIVateid '{0}{1}{2}@msg.pc.t-mobile.com'".format(MCC, MNC, IMSI))
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:AUTHenticati:SCHeme AKA1")
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:AUTHenticati:ALGorithm XOR")
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:AUTHenticati:AMF '0x000'")
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:RESLength 128")
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:IPSec:ENABle ON")
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:IPSec:ALGorithm:INTegrity HMMD")
                cmw.write("CONF:DATA:CONT:IMS2:SUBScriber1:IPSec:ALGorithm:ENCRyption NOC")

                # Configure Virtual Subscriber
                logger.debug('DAU IMS2 - Configure Virtual Subscriber')
                cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:BEHaviour ANSWER")
                cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:SIGNalingtyp NOPRecondit")
                cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:FORCemocall OFF")
                cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:BEARer OFF")
                cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:ADCodec:TYPE WIDeband")
                # cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:AMR:TYPE NARR")
                cmw.write('CONF:DATA:CONT:IMS2:VIRTualsub1:AMR:ALIGnment BANDwidtheff')
                # cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:AMR:ALIGnment OCTetaligned")
                cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:AMR:CODec3:ENABle ON")
                # cmw.write("CONF:DATA:CONT:IMS2:VIRTualsub1:AMR:CODec8:ENABle ON")
            else :
                logger.debug(" with  not Turning off the LTE signalling, DAU, Again ")

            loop_rst = loop_rst + 1

        # Configure LTE Signaling
        if 1:
            #time.sleep()
            logger.info('{0}'.format(132 * '-'))
            logger.info('Configure LTE Signaling')
            logger.info('LTE Cell - Set LTE Scenario To SISO')
            cmw.write(
                "ROUT:LTE:SIGN:SCEN:SCELl:FLEX SUA{0},{1},RX{2},{1},TX{2}".format(lte.sua, lte.rf_port, lte.converter))

            logger.info('LTE Cell - Set input and output path')
            logger.info(' including signal routing and Programming external attenuation.')
            cmw.write("CONF:LTE:SIGN:RFS:PCC:EATT:OUTP {0}".format(lte.dl_att))
            cmw.write("CONF:LTE:SIGN:RFS:PCC:EATT:INP {0}".format(lte.ul_att))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            lte.mode = "TDD" if int(TEST_BAND) in range(33, 42) else "FDD"
            logger.info('LTE Cell - Set LTE MODE to {0}'.format(lte.mode))
            cmw.write("CONF:LTE:SIGN:DMODe {0}".format(lte.mode))
            logger.info('{0}'.format(132 * '-'))

            if "TDD" in lte.mode:
                logger.info('{0}'.format(132 * '-'))
                logger.info('LTE - Set TDD ULDL to configuration 5')
                cmw.write("CONF:LTE:SIGN:CELL:ULDL 5")
                logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - Set System bandwidth')
            for k in lte.bw:
                if k == TEST_BW:
                     cmw.write("CONF:LTE:SIGN:CELL:BAND:DL B{0:03d}".format(int(10 * TEST_BW)))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - Set Operating Band and DL channel number')

            cmw.write("CONF:LTE:SIGN:BAND OB{0}".format(TEST_BAND))

            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('Set Down Link Channel to: {0}'.format(dl_channel))
            cmw.write("CONF:LTE:SIGN:RFS:CHAN:DL {0}".format(dl_channel))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - CELL ID')
            cmw.write("CONF:LTE:SIGN:CELL:PCID 0")
            logger.info('{0}'.format(132 * '-'))

            if cmw.sw_list.count('KS510') != 0:
                logger.info('{0}'.format(132 * '-'))
                logger.info('LTE Cell - CYCLE PREFIX')
                cmw.write("CONF:LTE:SIGN:CELL:CPR NORM")
                logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            cmw.write("CONF:LTE:SIGN:CELL:TIME:SATTach ON")
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - Define the RS EPRE level and the power of the DL channels and signals')
            logger.info(' Set RS EPRE level to {0:5.1f} dBm/FFT 15 KHz'.format(lte.rs_epre))
            cmw.write("CONF:LTE:SIGN:DL:RSEPre:LEVel {0:5.1f}".format(lte.rs_epre))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('Advance PRACH settings')
            cmw.write("CONF:LTE:SIGN:UL:PCC:APPower:EASettings ON")
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - Set POWER CONTROL')
            cmw.write("CONF:LTE:SIGN:UL:TPC:SET CLO")
            logger.info('Set LTE PUSCH Close LOOP Power to {0:5.1f} dBm'.format(float(tx_close_loop_target_power)))
            cmw.write("CONF:LTE:SIGN:UL:PUSCh:TPC:CLTPower {0:5.1f}".format(float(tx_close_loop_target_power)))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE - Set Connection Type.')

            if DAU_PRESENT:
                logger.info('LTE - Set Connection Type to Data Connection.')
                cmw.write("CONF:LTE:SIGN:CONNection:CTYPe DAPP")

            else:
                logger.info('LTE - Set Connection Type to Test Mode Connection.')
                cmw.write("CONF:LTE:SIGN:CONNection:CTYPe TEST")
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - Set Network Parameters')

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - Specify MCC MNC, tracking area code and E-UTRAN cell ID.')
            cmw.write("CONF:LTE:SIGN:CELL:MCC {0}".format(MCC))
            cmw.write("CONF:LTE:SIGN:CELL:MNC:DIG THR")
            cmw.write("CONF:LTE:SIGN:CELL:MNC {0}".format(MNC))
            cmw.write("CONF:LTE:SIGN:CELL:TAC 1")
            cmw.write("CONF:LTE:SIGN:CELL:SEC:AUTH ON")
            cmw.write("CONF:LTE:SIGN:CELL:SEC:NAS ON")
            cmw.write("CONF:LTE:SIGN:CELL:SEC:AS ON")
            cmw.write("CONF:LTE:SIGN:CELL:SEC:IALG S3G")
            cmw.write("CONF:LTE:SIGN:CELL:SEC:MIL OFF")
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE Cell - Specify the User IMSI.')
            cmw.write("CONF:LTE:SIGN:CELL:UEID:IMSI '{0}{1}{2}'".format(MCC, MNC, IMSI))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE - Set APN and CQI')
            cmw.write("CONF:LTE:SIGN:CONNection:APN '{0}'".format(lte.apn))
            cmw.write('CONF:LTE:SIGN:CONNection:QCI {0}'.format(lte.qci))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            if IMS_FLAG:

                logger.info('NAS IMS Call supported')
                cmw.write("CONF:LTE:SIGN:CELL:NAS:EPSNetwork ON")
                cmw.write("CONF:LTE:SIGN:CELL:NAS:IMSVops SUPP")

            else:

                logger.info('NAS IMS Call not supported')
                cmw.write("CONF:LTE:SIGN:CELL:NAS:EPSNetwork OFF")
                cmw.write("CONF:LTE:SIGN:CELL:NAS:IMSVops NSUP")

            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE - Set LTE stack to Accept Multiple Bearer.')
            cmw.write("CONF:LTE:SIGN:CONNection:AMDBearer ON")
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE - Set LTE stack to for Redirection Inter LTE Band Handover')
            cmw.write("CONF:LTE:SIGN:CONNection:OBCHange RED")

            logger.info('LTE - Set LTE stack to for Redirection Inter LTE Channel Handover')
            cmw.write("CONF:LTE:SIGN:CONNection:FCHange RED")
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('LTE - Reduce PDCCH')
            cmw.write("CONF:LTE:SIGN:CONNection:PDCCh:RPDCch ON")
            logger.info('{0}'.format(132 * '-'))
            #
            if cmw.sw_list.count('KS510') != 0:
                logger.info('{0}'.format(132 * '-'))
                logger.info(' Configure RMC Test Mode Call. (User Defined Channel)')
                cmw.write("CONF:LTE:SIGN:CONN:UET UDCH")
                logger.debug(c_lte().rb_d.values())
                for k in lte.bw:
                    if k == TEST_BW:
                        if k not in list(c_lte().rb_d.keys()):
                            raise ValueError('{0} not a valid BW - [{1}]'.format(TEST_BW, ",".join(str(b) for b in list(c_lte().rb_d.keys()))))
                        # this condition is for low value of RB
                        elif TEST_RB == 0 and Start_RB == 0:
                            # Set Starting Position to high
                            lte.nrb = TEST_RB
                            logger.debug("enter in to user RB")
                            pos = Start_RB
                            #cmw.write("CONF:LTE:SIGN:CONN:UDCH:DL {0},{0},QPSK,9".format(pos, lte.nrb))
                            #cmw.write("CONF:LTE:SIGN:CONN:UDCH:UL {0},{0},QPSK,10".format(pos, lte.nrb))
                        # this condition is for high value
                        elif TEST_RB >0 and Start_RB == 0:
                                lte.nrb =TEST_RB
                                for i in srb :
                                    if i == Start_RB:
                                        lte.nrb = TEST_RB
                                        pos = Start_RB

                        elif TEST_RB is not c_lte().rb_d[TEST_BW]:
                            logger.debug(132*'_')
                            logger.debug(" Please refer Test Document page, select supported RB for Selected BW  ")
                            logger.debug(132 * '_')

                        else :
                            lte.nrb = TEST_RB
                            pos = Start_RB

            if TEST_CH_TYPE == 'mid':
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:DL {0},{1},QPSK,2".format(lte.nrb, pos))
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:UL {0},{1},QPSK,1".format(lte.nrb, pos))
            elif TEST_CH_TYPE == 'low':
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:DL {0},{1},QPSK,2".format(lte.nrb, pos))
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:UL {0},{1},QPSK,1".format(lte.nrb, pos))
            elif TEST_CH_TYPE == 'high':
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:DL {0},{1},QPSK,2".format(lte.nrb, pos))
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:UL {0},{1},QPSK,1".format(lte.nrb, pos))
            else:
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:DL {0},{1},QPSK,2".format(lte.nrb, pos))
                cmw.write("CONF:LTE:SIGN:CONN:UDCH:UL {0},{1},QPSK,1".format(lte.nrb, pos))
            time.sleep(5)
            logger.info('{0}'.format(132 * '-'))

            erreur = cmw.ask("SYST:ERR:ALL?")
            if erreur[0] != '0':
                raise ValueError(erreur)


            logger.info('{0}'.format(132 * '-'))


            # End Configure LTE CELL
        # *****************************************************************************
        time.sleep(5)
        device.shell('settings put global airplane_mode_on 0')
        # NOTE: Some android versions require device.shell('su -c am broadcast -a android.intent.action.AIRPLANE_MODE')
        device.shell('am broadcast -a android.intent.action.AIRPLANE_MODE')

        # Start DAU services
        if DAU_PRESENT:
            logger.info('{0}'.format(132 * '-'))

            # Start DAU service
            logger.info(' Start DAU service(s)'.format(132 * '-'))

            for service in dau_service_l:

                logger.info('Start DAU {0} service'.format(service))
                status = cmw.ask("SOURce:DATA:CONT:{0}:STATe?".format(service))[0]

                if 'OFF' in status:
                    cmw.write("SOURce:DATA:CONT:{0}:STATe ON".format(service))

                    status = ''
                    while status != 'ON':
                        time.sleep(0.150)
                        status = cmw.ask("SOURce:DATA:CONT:{0}:STATe?".format(service))[0]

                logger.info('DAU service {0} is ON'.format(service))

            erreur = cmw.ask("SYST:ERR:ALL?")
            if erreur[0] != '0':
                raise ValueError(erreur)

            logger.info('{0}'.format(132 * '-'))

            # Init Fsw
        if 1:
            logger.info('{0}'.format(132 * '-'))
            logger.info('Create a Socket Class object to remote the fsw')
            kwargs = {'timeout': fsw_socket_timeout, 'temchar': fsw_socket_termchar}

            # get a socket instance for controlling fsW

            fsw = c_socket(fsw_host, fsw_socket_port, **kwargs)

            # connect to FSW
            fsw.connect()
            fsw.timeout = 40.0
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('QUERY ID')

            if not hasattr(fsw, 'id'):
                setattr(fsw, 'id', 'FSW')
            if not hasattr(fsw, 'sn'):
                setattr(fsw, 'sn', '000000')
            if not hasattr(fsw, 'BASE_FW'):
                setattr(fsw, 'BASE_FW', 'FSW')

            buffin = fsw.ask("*IDN?")
            logger.debug(buffin)

            # get fsw options
            logger.info('{0}'.format(132 * '-'))
            logger.info('QUERY fsw Option')
            if not hasattr(fsw, 'opt'):
                setattr(fsw, 'opt', [])
            fsw.opt = fsw.ask("*OPT?")

            # fsw scpi commands start

            logger.info('{0}'.format(132 * '-'))
            logger.info('RESET FSW')
            #  fsw reset & setting Attunation
            logger.debug(132 * '-')
            fsw.timeout = 30.0
            #fsw.write("*CLS")
            fsw.write("*RST")
            fsw.write("INIT:CONT OFF")
            fsw.write("SYST:PRES:ALL")
            time.sleep(0.5)
            fsw.write("SENSe:CORRection:TRANsducer:SELect 'dummy_FSW_pathloss'")
            fsw.write("SENSe:CORRection:TRANsducer:ON")
            fsw.write("SENSe:CORRection:TRANsducer:UNIT 'DB'")
            fsw.write("SENSe:CORRection:TRANsducer:COMMent 'Test Transducer'")
            fsw.write("SENSe:CORRection:TRANsducer:DATA 30e6,5, 12750e6,3")
            time.sleep(10)
            fsw.write("INIT:CONT ON")
            fsw.write("INP:ATT:AUTO OFF")
            fsw.write("INP:ATT 40")


        # Turn LTE Cell ON
        if 1:
            #
            logger.info('{0}'.format(132 * '-'))

            logger.info('TURN LTE CELL ON')
            cmw.write("SOUR:LTE:SIGN:CELL:STATe ON")

            TIMEOUT = 120.0
            tstart = time.time()
            buffin = cmw.ask("SOUR:LTE:SIGN:CELL:STAT:ALL?")
            while not (buffin[0] == 'ON' and buffin[1] == "ADJ"):

                buffin = cmw.ask("SOURce:LTE:SIGN:CELL:STAT:ALL?")

                time.sleep(0.5)
                if (time.time() - tstart) > TIMEOUT:
                    # x = win32api.MessageBox(0, "TIMEOUT occurs")
                    raise ValueError('TIMEOUT - LTE Signaling Turn OFF')

            logger.info('LTE CELL READY')
            logger.info('{0}'.format(132 * '-'))
            time.sleep(30)
            # Check Default Bearers
            TIMEOUT = 30
            # changed
            tstart = time.time()
            buffin = cmw.ask('CATalog:LTE:SIGN:CONNection:DEFBearer?')[0] ##{ ["5 (Test Network)","6 (ims)"]}
            logger.debug("Bearers in buffin {0}".format(buffin))
            state = cmw.ask('SENSE:LTE:SIGN:RRCState?')[0]
            logger.debug("cmw RRC state is : {0}".format(state))
            device.shell('ip addr >DUT_ip.txt')
            device.shell('devices')
            while not "5 (Test Network)" in buffin:
                buffin = cmw.ask('CATalog:LTE:SIGN:CONNection:DEFBearer?')[0]
                time.sleep(0.5)
                if (time.time() - tstart) > TIMEOUT:
                    logger.info('TIMEOUT - Default Bearers not present')
                    # Toggle airplane mode on -> off
                    #device.shell('root')
                    #time.sleep(2.0)
                    device.shell('settings put global airplane_mode_on 1')
                    # NOTE: Some android versions require device.shell('su -c am broadcast -a android.intent.action.AIRPLANE_MODE')
                    device.shell('am broadcast -a android.intent.action.AIRPLANE_MODE')
                    time.sleep(2.0)
                    device.shell('settings put global airplane_mode_on 0')
                    device.shell('am broadcast -a android.intent.action.AIRPLANE_MODE')
                    time.sleep(2.0)
                    # wait for dut to register
                    logger.info('waiting for dut to register. airplane mode on -> off')
                    start_register_time = time.time()
                    registered = False
                    while not registered and time.time() < start_register_time + REGISTER_TIMEOUT:
                        register_state = cmw.ask('FETCH:LTE:SIGN:PSW:STATe?')[0]
                        rrc_state = cmw.ask('SENSE:LTE:SIGN:RRCState?')[0]
                        logger.info('connection state : %s : %s', register_state, rrc_state)

                        if rrc_state == 'CONN':
                            registered = True

                        else :
                            time.sleep(1.0)
                            device.shell('reboot')
                            time.sleep(80)
                    if not registered:
                        logger.error('dut did not register successfully. terminating.')
                        #sys.exit(-3)

                    logger.info('dut did register successfully.')
            logger.info('Default Bearer detected')
            # device.shell('ifconfig')
            ip_addr = device.shell('netcfg')
            logger.debug(ip_addr)

            # device.shell('ip addr')

            for i in buffin:
                if i == "5 (Test Network)":
                    result = "PASS"
                else:
                    result = "FAIL"
                    """
	   
	   
	        # Opening BLER Window for RX Meas
        
            logger.debug('Bler measurement')
            cmw.write("CONFigure:LTE:SIGN:CONNection:DLPadding ON")
            cmw.write("CONFigure:LTE:SIGN:EBLer:SCONdition CLEV")
            cmw.write("CONFigure:LTE:SIGN:EBLer:SFRames 10000")
            cmw.write("CONFigure:LTE:SIGN:EBLer:ERCalc ERC1")
            cmw.write("CONFigure:LTE:SIGN:EBLer:CONFidence:OASCondition ACWait")
            cmw.write("CONFigure:LTE:SIGN:EBLer:CONFidence:MTTime 0")
            cmw.write("CONFigure:LTE:SIGN:EBLer:CONFidence:LERate P050")


            cmw.write("CONFigure:LTE:SIGN:EBLer:SCONdition CLEV")
            cmw.write("INITiate:LTE:SIGN:EBLer")
            cmw.write("FETCh:LTE:SIGN:EBLer:PCC:CONFidence?")
            
            
            cmw.write("INIT:LTE:SIGN:EBLer")
            Bler_State= cmw.write("FETCh:LTE:SIGN:EBLer:STATe:ALL?")
            logger.debug("Bler State is {0}".format(Bler_State))
            Bler_PCC_Abs= cmw.write("FETCh:INTermediate:LTE:SIGN:EBLer:PCC:ABSolute?")
            logger.debug("Bler PCC absolute is {0}".format(Bler_PCC_Abs))
            Bler_PCC_Rel= cmw.write("FETCh:INTermediate:LTE:SIGN:EBLer:PCC:RELative?")
            logger.debug("Bler PCC relative is {0}".format(Bler_PCC_Rel))
            """

            fsw.write("SWE:MODE LIST")
            logger.info('{0}'.format(132 * '-'))
            logger.info('SCPI commands for FSW')
            logger.info('{0}'.format(132 * '-'))
            fsw.write("INIT:CONT OFF")
            fsw.write("LIST:RANG:COUNt?")

            fsw.write("LIST:RANG4:DEL")

            # range
            count = 1
            for (strt, stp, rbw, vbw, swp, lmt) in zip(freq_start, freq_stop, rbw_in, vbw_in, sweep_point_value, limit):
                fsw.write("LIST:RANG{0}:STAR {1}".format(count, strt))  # fsw.write("LIST:RANG1:STAR 3000000000")
                fsw.write("LIST:RANG{0}:STOP {1}".format(count, stp))
                fsw.write("LIST:RANG{0}:BAND {1}".format(count, rbw))
                fsw.write("LIST:RANG{0}:BAND:VID {1}".format(count, vbw))
                fsw.write("LIST:RANG{0}:INP:ATT:AUTO OFF".format(count))
                fsw.write("LIST:RANG{0}:INP:ATT {1}".format(count, att_rf))
                #fsw.write("SENS:LIST:RANG{0}:TRAN {1}".format(count, transducer))

                fsw.write("LIST:RANG{0}:DET {1}".format(count, str(detector_type)))
                fsw.write("LIST:RANG{0}:POIN {1}".format(count, swp))
                fsw.write("LIST:RANG{0}:RLEV {1}".format(count, ref_lev))
                fsw.write("LIST:RANG{0}:SWE:TIME {1}".format(count, sweep_time))
                fsw.write("LIST:RANG{0}:LIM:STAR {1}".format(count, lmt))
                fsw.write("LIST:RANG{0}:LIM:STOP {1}".format(count, lmt))
                if count == 1:
                    fsw.write("LIST:RANG3:DEL")
                count = count + 1
                fsw.write(132 * '-')



            """
            #PreAmplifier
            fsw.write("SENS:LIST:RANG1:INP:GAIN:STAT OFF")
            fsw.write("SENS:LIST:RANG2:INP:GAIN:STAT OFF")
            fsw.write("SENS:LIST:RANG3:INP:GAIN:STAT OFF")
            fsw.write("SENS:LIST:RANG4:INP:GAIN:STAT OFF")

            #fsw.write("SENS:LIST:RANG1:INP:GAIN:STAT 15")
            #fsw.write("SENS:LIST:RANG2:INP:GAIN:STAT 15")
            #fsw.write("SENS:LIST:RANG3:INP:GAIN:STAT 15")
            #fsw.write("SENS:LIST:RANG4:INP:GAIN:STAT 15")
            """


            fsw.write("LIST:RANG:LIM:STAT ON")
            fsw.write("CALC:PSE:MARG 100")
            fsw.write("CALC:PSE:PSH ON")
            fsw.write("CALC:PSE:SUBR 1")
            fsw.result = fsw.ask("CALC:LIM1:FAIL?")
            logger.debug('result is: {0}'.format(fsw.result)) # this scpi
            fsw.write("INIT:SPUR; *WAI")
            #time.sleep(5)
            list_of_Freq = fsw.ask("TRAC:DATA? SPURIOUS")# when it returns, at that time length of list_freq ==1
            # only one value values


            fsw.write("FORM:DEXP:FORM CSV")
            fsw.write("FORM:DEXP:DSEP POIN")
            fsw.write("FORM:DEXP:FORM CSV")
            fsw.write("FORM:DEXP:HEAD ON")
            fsw.write("FORM:DEXP:TRAC SING")

            # Directory path of csv

            fsw.write("MMEM:STOR1:TRAC 1,'C:\\R_S\\instr\\user\\fsw_Results_{0}.CSV'".format(row_count))
            logger.debug(len(list_of_Freq))
            logger.debug(list_of_Freq)


            if len(list_of_Freq) == 6:

                # Printing the Spurious emissions verdict
                logger.debug(list_of_Freq)

                n = 3
                m = np.array(list_of_Freq)
                y = m.astype(float)
                z = y.tolist()
                Meas_range = [z[i:i + n] for i in range(0, len(z), n)]


                def Extract(Meas_range):
                    Freq = list(map(itemgetter(0), Meas_range))
                    Power_abs = list(map(itemgetter(1), Meas_range))
                    Limit_p = list(map(itemgetter(2), Meas_range))
                    return Freq, Power_abs, Limit_p


                Meas = Extract(Meas_range)
                min = -47.0
                max = -57.0

                if Meas[1][1] < float(min) and Meas[1][0] < float(max):
                    summary = 'PASS'
                else:
                    summary = 'FAIL'
                abs_fre = [Meas[1][0], Meas[1][1]]
                logger.debug ("abs power msew value are {0} {1}".format(Meas[1][0], Meas[1][1]))
                # Measured values of ranges 1,2,3 should be less than -36 dbm

                if Meas[1][0] < float(max):
                    verdict = 'PASS'
                else:
                    verdict = 'FAIL'
                if Meas[1][1] < float(min):
                    verdict = 'PASS'
                else:
                    verdict = 'FAIL'

                logger.debug(Meas)
                logger.debug(132 * '-')
                logger.debug("Measurement Ranges for FSW spectrum analyzer")
                logger.debug(132 * '-')
                logger.debug(" Range  |  Freq  kHZ| PowerAbs(-dbm) |  limit (-db) | Verdict  ")
                logger.debug(
                    " Range1 | {0:.05f}     | {1:.02f} |  {2:.02f} |{3}  ".format(Meas[0][0] / 1000, Meas[1][0],
                                                                                  Meas[2][0],
                                                                                  verdict))
                logger.debug(
                    " Range2 | {0:.05f}     | {1:.02f} |  {2:.02f}  |{3} ".format(Meas[0][1] / 1000, Meas[1][1],
                                                                                  Meas[2][1],
                                                                                  verdict))

                logger.debug(132 * '-')
                logger.debug(" Test Summary for Frequency Measurement for all ranges : {0}  ".format(summary))
                logger.debug(132 * '-')
                # writing to file Fsw measuremnt
                ranges = [1, 2]
                freq_ranges = [Meas[0][0], Meas[0][1]]
                abs_power = [Meas[1][0], Meas[1][1]]
                limit = [Meas[2][0], Meas[2][1]]


                # dictionary of lists
                dict = {'Range': ranges, 'RBW':rbw_in, 'frequency': freq_ranges, 'abs_power': abs_power, 'limit_pwr': limit}
                df = pd.DataFrame(dict)
                timestr = time.strftime("%Y%m%d-%H%M%S")
                # saving the dataframe
                logger.debug(132 * '_')
                logger.debug(mydir_d)
                logger.debug(132 * '_')
                df.to_csv('{3}\\fsw_logsresult_{0}_band{1}_{2}.csv'.format(TEST_BW, TEST_BAND, timestr, mydir_d), index=False,
                          mode='a')
                # logger.debug('\\mydir_d\\fsw_msmt_{0}_band{1}_{2}.csv'.format(TEST_BW, TEST_BAND, timestr))


            elif len(list_of_Freq) == 3:

                # Printing the Spurious emissions verdict
                logger.debug(list_of_Freq)
                #[ freq, abs, limit]
                n = 1
                m = np.array(list_of_Freq)
                y = m.astype(float)
                z = y.tolist()
                Meas_range = [z[i:i + n] for i in range(0, len(z), n)]
                def Extract(Meas_range):
                    Freq = list(map(itemgetter(0), Meas_range))
                    Power_abs = list(map(itemgetter(1), Meas_range))
                    Limit_p = list(map(itemgetter(2), Meas_range))
                    return Freq, Power_abs, Limit_p
                    Meas = Extract(Meas_range)
                    min = -47.0
                    max = -57.0
                    if Meas[1] < float(max):
                        summary = 'PASS'
                    else:
                        summary = 'FAIL'
                    abs_fre = [Meas[1]]
                    logger.debug("abs power msew value are {0} {1} {2} {3}".format(Meas[1]))
                    # Measured values of ranges 1,2,3 should be less than -36 dbm
                    if Meas[1] < float(max):
                        verdict = 'PASS'
                    else:
                        verdict = 'FAIL'

                    logger.debug(Meas)
                    logger.debug(132 * '-')
                    logger.debug("Measurement Ranges for FSW spectrum analyzer")
                    logger.debug(132 * '-')
                    logger.debug(" Range  |  Freq  kHZ| PowerAbs(-dbm) |  limit (-db) | Verdict  ")
                    logger.debug(
                            " Range1 | {0:.05f}     | {1:.02f} |  {2:.02f} |{3}  ".format(Meas[0] / 1000, Meas[1],
                                                                                          Meas[2],
                                                                                          verdict))
                    logger.debug(132 * '-')
                    logger.debug(" Test Summary for Frequency Measurement for all ranges : {0}  ".format(summary))
                    logger.debug(132 * '-')
                    # writing to file Fsw measuremnt
                    ranges = [1]
                    freq_ranges = [Meas[0]]
                    abs_power = [Meas[1]]
                    limit = [Meas[2]]

                    # dictionary of lists
                    dict = {'Band: band_info, Range': ranges, 'RBW': rbw_in, 'frequency': freq_ranges,
                            'abs_power': abs_power, 'limit_pwr': limit}

                    df = pd.DataFrame(dict)
                    timestr = time.strftime("%Y%m%d-%H%M%S")
                    # saving the dataframe
                    logger.debug(132 * '_')
                    logger.debug(mydir_d)
                    logger.debug(132 * '_')
                    df.to_csv('{3}\\fsw_logsresult_{0}_band{1}_{2}.csv'.format(TEST_BW, TEST_BAND, timestr, mydir_d), index=False,
                                  mode='a')
                    # logger.debug('\\mydir_d\\fsw_msmt_{0}_band{1}_{2}.csv'.format(TEST_BW, TEST_BAND, timestr))

            else :
                logger.debug(" fsw intialization fail or either FSW spurious msmt  values are 1 or 0 ")
                logger.debug("FSW scipi command fsw.ask(TRAC:DATA? SPURIOUS) returns either value 1  or 0 in msmt list ")
            logger.debug(132 * '_')
            logger.debug(132 * '_')
        # End Init FSW
            """
            # Set Dedicated Bearer ID to 6(ims), profile Voice
            cmw.write('PREPare:LTE:SIGN:CONN:DEDBearer "6 (ims)", VOICE, 1, 65535')
            # Connect Dedicated Bearer
            cmw.write('CALL:LTE:SIGN:PSWitched:ACTion CONNect')
            # Query Dedicated Bearer
            buffin = cmw.ask("CATalog:LTE:SIGN:CONNection:DEDBearer?")[0]
            while not "(->6, Voice)" in buffin:
                buffin = cmw.ask("CATalog:LTE:SIGN:CONNection:DEDBearer?")[0]
                time.sleep(0.5)
            logger.info('Dedicated Bearer Voice connected')
            logger.debug("PASSED")

        

            # Initiate VoLTE call to UE:
        cmw.write("CONFigure:DATA:CONTrol:IMS2:VIRTualsub1:MTCall:CALL")
        time.sleep(2)
        buffin = cmw.ask("SENSe:DATA:CONTrol:IMS2:EVENts:LAST?")
        if 'RING' in buffin:
            logger.info('VoLTE call to UE initiated')
        else:
             pass

        # Answer call in UE
        device.shell("input keyevent 5")
        logger.info('UE device answering incoming call from CMW')
        time.sleep(2)

        buffin = cmw.ask("SENSe:DATA:CONTrol:IMS2:EVENts:LAST?")
        if 'EST' in buffin:
            logger.info('VoLTE call established')
            result = 'PASS'
        else:
            result = 'FAIL'
            #pass

            time.sleep(5)

            # Terminate call in UE
            device.shell("input keyevent 6")
            logger.info('UE device terminating call from CMW')
            #
            #device.shell("reboot")
            time.sleep(2.0)
            #write Summary  pass/fail with combination of input parameters
            """

        logger.debug("PASSED")
        erreur = cmw.ask("SYST:ERR:ALL?")
        #result ='PASS'
        logger.debug("Band: 	\t Bandwidth : (MHz) \t	DL Frequency:  (MHz)	\tRB Allocation: 	\t RB Start: 	\t float(Power Level)       \t Channel type")
        logger.debug(" {0}	 \t\t  :{1} (MHz) \t\t	: {2} (MHz)\t	\t\t: {3}	   \t\t\t : {4}	\t\t\t  {5}  \t\t\t {6} ".format(TEST_BAND, TEST_BW, TEST_FREQ_DL, TEST_RB, Start_RB, Power_level_TYPE, summary ))
        # socket class

        lte_Rx_result = {'band': [TEST_BAND], 'BandWidth':[TEST_BW], 'DL Frequency': [TEST_FREQ_DL], 'RB Allocation': [TEST_RB], 'RB Start': [Start_RB], '@power' : [Power_level_TYPE], 'Summary': [summary]}

        output = pd.DataFrame(lte_Rx_result)
        #now_re = datetime.(now)
        timestr_cmw = time.strftime("%Y%m%d-%H%M%S")
        #dt_re_string = now.strftime("%d_%m_%Y_%H_%M_%S")
        # saving the dataframe
        logger.debug(132 * '_')
        logger.debug(mydir_d)
        logger.debug(132 * '_')
        output.to_csv('{1}\\CMW_logsresult_{0}.csv'.format(timestr_cmw, mydir_d), index=False, mode='a')

        #row_count = row_count + 1
        logger.info('entering in instrument section')
        """
        if erreur[0] != '0':
            raise ValueError(erreur)
        logger.info('{0}'.format(132 * '-'))
        """
        rth = RsInstrument('TCPIP::192.168.0.219::INSTR')
        rm = pyvisa.ResourceManager()
        instr = rm.open_resource('TCPIP::192.168.0.219::INSTR')  # replace by your IP-address
        instr.timeout = 3000
        logger.info('entering in instrument section')

        instr.write('INIT:CONT OFF')

        # truns on color printing
        instr.write('HCOP:DEV:COL ON')

        # select file format
        # (WMF | GDI | EWMF | BMP | PNG | JPEG | JPG | PDF | SVG | DOC | RTF)
        instr.write('HCOP:DEV:LANG PNG')
        # rth.write_str("HCOP:LANG PNG")

        # set print to file
        instr.write('HCOP:DEST "MMEM"')
        logger.debug(132 * '_')
        logger.debug(mydir_d)
        logger.debug(132 * '_')
        filePathInstr = r"/temp/spurious_emi{0}_{1}_{2}.png".format(TEST_BAND, TEST_BW, timestr_cmw)  # size of 18kb
        filePathPc = r"{3}\\spurious_emi{0}_{1}_{2}.png".format(TEST_BAND, TEST_BW, timestr_cmw, mydir_d)  # no data

        # file path on instrument
        instr.write('MMEM:NAME "{}"'.format(filePathInstr))

        # create screenshot
        instr.write("HCOP:IMM")

        # ask for file data from instrument
        fileData = instr.query_binary_values('MMEM:DATA? "{}"'.format(filePathInstr), datatype='s')[0]
        # print(type(fileData))
        # time.sleep(20)

        rth.write_str(f"MMEM:NAME '{filePathInstr}'")
        rth.write_str_with_opc("HCOP:IMM")
        rth.read_file_from_instrument_to_pc(filePathInstr, filePathPc)

        print(instr.query('SYST:ERR?'))

        instr.close()


    # catch error
    except Exception as Err:

        logger.error(Err)
        logging.traceback.print_exc()


    finally:

        # close CMW class
        if cmw is not None:
            cmw.write('&GTL')
            cmw.close()
            cmw = None
    row_count = row_count + 1
    logger.debug( "end of {0} th loop".format(int(row_count)))
    #logger.debug("PASSED")
    #device.shell('settings put global airplane_mode_on 1')
    # NOTE: Some android versions require device.shell('su -c am broadcast -a android.intent.action.AIRPLANE_MODE')
    #device.shell('am broadcast -a android.intent.action.AIRPLANE_MODE')
# end of While loop
# Storing all csv file in to single file to conclude the results summary for all runs
timestr_out = time.strftime("%Y%m%d")
logger.debug(132*'_')
logger.debug(mydir_d)
logger.debug(132 * '_')
#defining glob function to aggregate the CMW, FSW CSV files
""""
def csv_group(inst_log):
    cmw_csv_files = glob("{0}\\{1}_logsresult_*.csv".format(mydir_d, inst_log))
    df = pd.concat((pd.read_csv(f, header = 0) for f in cmw_csv_files))
    timestr_f = time.strftime("%Y%m%d-%H%M%S")
    df.to_csv("{1}\\{2}_VERDICT_{0}.csv".format(timestr_f, mydir_d, inst_log))
#FSW MSMT verdict

csv_group('CMW')
csv_group('FSW')
"""
logger.debug(132 * '_')
logger.debug("df")


cmw_csv_files = glob("{1}\\CMW_*.csv".format(timestr_out, mydir_d))
#creating pandas data frame dict for cmw csv files
df = pd.concat((pd.read_csv(f, header = 0) for f in cmw_csv_files))
logger.debug(df)
timestr_f = time.strftime("%Y%m%d-%H%M%S")
CMW_verdict = 'CMW_VERDICT_{0}'.format(timestr_f)#CMW_VERDICT_20210221-221813
#writing csv files
df.to_csv("{1}\\{0}.csv".format(CMW_verdict, mydir_d), index=False)
#writing on to csv files content to json file
#df.to_json (r'{0}\\cmw_ctf_j.json'.format(mydir_d), orient='split' )

FSW_verdict = 'FSW_VERDICT_{0}'.format(timestr_f)
fsw_csv_files = glob("{1}\\fsw_*.csv".format(timestr_out, mydir_d))
df_fsw = pd.concat((pd.read_csv(f, header=0 ) for f in fsw_csv_files))
df_fsw.to_csv("{1}\\{0}.csv".format(FSW_verdict, mydir_d), index=False)

# converting csv file to json
#df_j = pd.read_csv (r'{0}\\{1}.csv'.format(mydir_d, CMW_verdict))


#df_j.reset_index(inplace=True)
#df_j.to_json (r'{0}\\ctf_j.json'.format(mydir_d))
# printing the csv contents in run log .py for all variants
#logger.debug(df_j)
"""
def csv_to_json(csvFilePath, jsonFilePath):
    jsonArray = []

    # read csv file
    with open(csvFilePath, encoding='utf-8') as csvf:
        # load csv file data using csv library's dictionary reader
        csvReader = csv.DictReader(csvf)

        # convert each csv row into python dict
        for row in csvReader:
            # add this python dict to json array
            jsonArray.append(row)

    # convert python jsonArray to JSON String and write to file
    with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
        jsonString = json.dumps(jsonArray, indent=4)
        jsonf.write(jsonString)


csvFilePath = r"{0}\\{1}.csv".format(mydir_d , CMW_verdict)
logger.debug(csvFilePath)
jsonFilePath = r"C:\\Test\\Cmw_data.json"
csv_to_json(csvFilePath, jsonFilePath)
"""
#moving csv files and json files to results_run folder
#shutil.move(os.path.join(mydir_d, ), os.path.join(dest_d))
shutil.copytree(mydir_d, dest_d,dirs_exist_ok=True )


# converting fsw verdict csv file to json
df_f = pd.read_csv (r'{0}\\{1}.csv'.format(mydir_d, FSW_verdict))
#df_j.to_json (r'{0}\\ctf_j.json'.format(mydir_d))
df.to_json (r'{0}\\ctf_fsw.json'.format(mydir_d), orient='split')
# printing the csv contents in run log .py for all variants
#logger.debug(df_j)
"""
This script:
1. collects the test case csv filenames into a list
2. reads each csv file into a dataframe
3. convert Series to a dictionary, adds data sources to json
4. adds specified charts
5. save data series to json file for visualization
# Sample usage
    cv = CtfVisualization(path=<path to test case files directory>)
    cv.create_json()
Note: Remove any non test case csv files from directory before running to prevent conflict 
or extraneous data from being included in the visualization.
"""




class CtfVisualization:
    """Interface to create the visualization data json file from csv results files"""
    _description: str  # not currently used
    _name: str
    _path: str
    _data_sources: list

    def __init__(self, description: str = "Visualize test case csv files", name: str = "ctf_cmw.json", path: str = ""):
        self._description = description
        self._name = name
        self._path = path
        self._data_sources = []

    def create_json(self):
        # CTF create data blob
        ctf_json = CtfJsonData(name=self._name, path=self._path)

        all_csv_files = glob(os.path.join(self._path, "CMW_VERDICT_*.csv"))
        for fn in all_csv_files:
            df = pd.read_csv(fn, sep=',', na_filter=False)

            # CTF add data source and table
            ctf_data_source = os.path.basename(fn)
            self._data_sources.append(ctf_data_source)
            ctf_json.add_data_source(ctf_data_source)
            ctf_columns = (', '.join(df))
            ctf_json.add_table(title=ctf_data_source, columns=ctf_columns, data_source_list=ctf_data_source)

            # CTF add data to source
            df_dict_ctf = df.T.to_dict()
            for row in df_dict_ctf:
                ctf_json.add_data_to_source(ctf_data_source, [df_dict_ctf[row]])

        # CTF dump to JSON file
        ctf_json.save_data()


# Sample usage
if __name__ == "__main__":
    cv = CtfVisualization(path=dest_d)
    cv.create_json()
    


logger.debug(132 * '_')
logger.debug("PASSED")

# THE END
