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
name_file = 'wifi'
std_wifi = '802.11g'
# Making a directory For the Run
#mydir = os.path.join('{0}\\Wifi_Logs_folder\\'.format(os.getcwd().split('W')[0]), '{0}_{1}_{2}'.format(name_file, datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), std_wifi))
mydir = os.path.join('{0}\\Wifi_Logs_folder\\'.format(os.getcwd().split('D')[0]), '{0}_{1}'.format(sys.argv[1], datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')))
os.makedirs(mydir)
mydir_d = mydir.replace('\\', '\\\\')
logger.debug("Result log folder created succesfully {0}".format(mydir_d))
# get a logging file handle
#if already dest_d file exits, delete and then create
#shutil.rmtree(os.path.join('{0}\\Logs_folder\\'.format(os.getcwd().split('D')[0]), 'LTE_TX_{0}_{1}'.format(sys.argv[1], sys.argv[4])))
#Creating directory for results
dest = os.path.join('{0}\\Wifi_Logs_folder\\'.format(os.getcwd().split('D')[0]), 'WLAN_RX_{0}'.format(sys.argv[1]))
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

# set log level
logger.setLevel(logging.DEBUG)


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

class c_wlan(object):

    def __init__(self):
        self.sua = "012"
        self.rf_port = "RF2C"  # For WIFI
        self.converter = 1
        #self.imsi = '310260123456789'
        #self.dl_att = 0.0
        #self.ul_att = 0.0
        self.std = "IEEE 802.11g"
        self.bw = 20
        self.channel = 1
        self.Tx_Burst_power = -40.0
        self.Rx_expected_power = 0.0

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
wlan = True

REGISTER_TIMEOUT = 120

dau_service_l = ['DNS', 'FTP', 'HTTP', 'IMS2', 'EPDG']



epdg_ip_v4 = "192.168.1.201"
epdg_ip_v6 = "fc01::1"
dau_ipv4_config = 'internal'
dau_ipv6_config = 'internal'

wlan = c_wlan()

wlan.sua = "012"
wlan.rf_port = "RF2C"
wlan.converter = 1
wlan.dl_att = 1.0
wlan.ul_att = 1.0
#wlan.std = "IEEE 802.11g"
wlan.bw = 20
wlan.channel = 1
wlan.Tx_Burst_power = -70.0
wlan.Rx_expected_power = 30.0

try:

    # read json file
    data = None
    f_json = os.path.curdir + os.sep + 'CONFIG_WLAN_TX.json'
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
        if 'wlan' in data:
            wlan.sua = data['wlan']['sua']
            wlan.rf_port = data['wlan']['rf_port']
            wlan.converter = data['wlan']['converter']
            wlan.dl_att = data['wlan']['dl_att']
            wlan.ul_att = data['wlan']['ul_att']
            wlan.std = data['wlan']['std']
            wlan.bw = data['wlan']['bw']
            wlan.channel = data['wlan']['channel']
            wlan.Tx_Burst_power = data['wlan']['Tx_Burst_power']
            wlan.Rx_expected_power = data['wlan']['Rx_expected_power']
            wlan.imsi = data['wlan']['imsi']


        MCC = wlan.imsi[0:3]
        MNC = wlan.imsi[3:6]
        IMSI = wlan.imsi[6:]

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
                sweep_point_value = data['fsw_params']['sweep_points']  # [ 800, 5000, 3300, 34000 ]
            if 'ranges' in data['fsw_params']:
                range_num = data['fsw_params']['ranges']  # [ 800, 5000, 3300, 34000 ]
            if 'ref_lev' in data['fsw_params']:
                ref_lev = data['fsw_params']['ref_lev']
            if 'att_rf' in data['fsw_params']:
                att_rf = data['fsw_params']['att_rf']
            if 'freq_start' in data['fsw_params']:
                freq_start = data['fsw_params']['freq_start']
            if 'freq_stop' in data['fsw_params']:
                freq_stop = data['fsw_params']['freq_stop']
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



            if 'wlan' in data:
                wlan.sua = data['wlan']['sua']
                wlan.rf_port = data['wlan']['rf_port']
                wlan.converter = data['wlan']['converter']
                wlan.dl_att = data['wlan']['dl_att']
                wlan.ul_att = data['wlan']['ul_att']
                wlan.std = data['wlan']['std']
                wlan.bw = data['wlan']['bw']
                wlan.channel = data['wlan']['channel']
                wlan.Tx_Burst_power = data['wlan']['Tx_Burst_power']
                wlan.Rx_expected_power = data['wlan']['Rx_expected_power']

#       MNC = wlan.imsi[3:6]
#       IMSI = wlan.imsi[6:]
#      #SIM = 'TMO'

    # get argument parsed
    if '--cmw' in sys.argv:
        cmw_host = sys.argv[sys.argv.index("--cmw") + 1]

    logger.info('{0}'.format(132 * '-'))
    logger.info('Get working directory')
    workdir = os.getcwd()
    logger.info('{0}'.format(workdir))
    logger.info('{0}'.format(132 * '-'))
    time.sleep(10)

    # Init CMW
    #Create a Socket Class object to remote the CMW
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


        time.sleep(5)
        cmw.write('SYST:DISP:UPD ON')
        logger.info('{0}'.format(132 * '-'))
        logger.info('RESET CMW')

        cmw.timeout = 1080.0

        cmw.write("*CLS")
        cmw.write("SYST:PRES:ALL")
        cmw.ask("*OPC?")
        cmw.timeout = 10.0

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


        # get CMW WLAN FW revision
        logger.info('{0}'.format(132 * '-'))
        logger.info('QUERY WLAN FW Revision')
        if not hasattr(cmw, 'wlan_sign_fw'):
            setattr(cmw, 'wlan_sign_fw', [])
        cmw.wlan_sign_fw = cmw.ask("SYST:OPT:VERS? \"CMW_WLAN_Sig\"")[0][1:-1]

        if not hasattr(cmw, 'wlan_mev_fw'):
         setattr(cmw, 'wlan_mev_fw', [])
        cmw.wlan_mev_fw = cmw.ask("SYST:OPT:VERS? \"CMW_WLAN_Meas\"")[0][1:-1]
        logger.info('{0}'.format(132 * '-'))

        # Check presence of DAU
        logger.info('{0}'.format(132 * '-'))
        if cmw.hw_list.count("H450A") != 0 or cmw.hw_list.count("H450B") != 0 or cmw.hw_list.count(
                "H450D") != 0 or cmw.hw_list.count("H450H") != 0 or cmw.hw_list.count("H450I") != 0:
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
        #wlan - TURN WLAN CELL OFF
        if 1:

            logger.info('{0}'.format(132 * '-'))
            logger.info('wlan - TURN WLAN CELL OFF')
            buffin = cmw.ask("SYST:SIGNaling:ALL:OFF;*OPC?")

            TIMEOUT = 120.0

            tstart = time.time()

            buffin = cmw.ask("SOUR:WLAN:SIGN:STAT:ALL?")
            while not (buffin[0] == "OFF" and buffin[1] == "ADJ"):

                # wait 500 ms
                time.sleep(0.5)

                # query WLAN CELL state
                buffin = cmw.ask("SOURce:WLAN:SIGN:STAT:ALL?")

                # check TIMEOUT
                if (time.time() - tstart) > TIMEOUT:
                    # x = win32api.MessageBox(0, "TIMEOUT occurs")
                    raise ValueError('TIMEOUT - WLAN Signaling Turn OFF')
                #
            logger.info('WLAN Cell - WLAN  IS TURN OFF')
            logger.info('{0}'.format(132 * '-'))




        # Configure DAU
        if DAU_PRESENT:

            logger.info('{0}'.format(132 * '-'))
            logger.info('DAU Configure Services')

            for service in dau_service_l:

                # Check DAU service
                status = cmw.ask("SOURce:DATA:CONT:{0}:STATe?".format(service))[0]
                logger.debug("Status of DAU : {0}".format(status))

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
                """    

                buffin = cmw.ask("CONFigure:DATA:CONTrol:IPVSix:ADDRess:TYPE?")[0]
                if buffin != "AUTO":
                    cmw.ask("CONFigure:DATA:CONTrol:IPVSix:ADDRess:TYPE AUTO;*OPC?")
                    """

            # DAU -  Configure DNS Service
            logger.debug('DAU -  Configure DNS Service')
            cmw.write(
                'CONFigure:DATA:CONT:DNS:LOCal:ADD "epdg.epc.mnc{0}.mcc{1}.pub.3gppnetwork.org", "{2}"'.format(MNC, MCC,
                                                                                                               epdg_ip_v4))
            cmw.write(
                'CONFigure:DATA:CONT:DNS:LOCal:ADD "epdg.epc.mnc{0}.mcc{1}.pub.3gppnetwork.org", "{2}"'.format(MNC, MCC,
                                                                                                               epdg_ip_v6))


            # Configure WLAN CELL
            #WIFI SIGN CONFIGURATION
            logger.info('WLAN - Configuring WLAN Signaling')
            logger.info('{0}'.format(132 * '-'))


            logger.info('WLAN - Routing WLAN Configuration')
            cmw.write("ROUT:WLAN:SIGN:SCEN:SCEL1:FLEXible SUA{0},{1},RX{2},{1},TX{2}".format(wlan.sua, wlan.rf_port,wlan.converter))


            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('WLAN - Set Attenuation Path Compensation')

            cmw.write("CONF:WLAN:SIGN:RFS:ANT1:EATT:OUTP {0}".format(wlan.dl_att))
            cmw.write("CONF:WLAN:SIGN:RFS:ANT1:EATT:INP {0}".format(wlan.ul_att))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('WLAN - Set WLAN SIGnaling in  AP mode')
            cmw.write("CONFigure:WLAN:SIGN:CONN:OMODe AP")
            logger.info('{0}'.format(132 * '-'))

            # Take user input for Standard
            logger.info('{0}'.format(132 * '-'))
            standard = {'key1':"IEEE 802.11a",'key2':"IEEE 802.11b",'key3':"IEEE 802.11g",'key4':"IEEE 802.11g(OFDM)",'key5':"IEEE 802.11a/n",'key6':"IEEE 802.11g/n",'key7':"IEEE 802.11g(OFDM)",'key8':"IEEE 802.11ac",'key9':"IEEE 802.11ax"}
            choice = sys.argv[1]

            if choice == standard['key1']:
                logger.info('WLAN Cell - Set 802.11a standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard ASTD")
            elif choice == standard['key2']:
                logger.info('WLAN Cell - Set 802.11b standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard BSTD")
            elif choice == standard['key3']:
                logger.info('WLAN Cell - Set 802.11g standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard GSTD")
            elif choice == standard['key4']:
                logger.info('WLAN Cell - Set 802.11g(OFDM) standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard GOSTd")
            elif choice == standard['key5']:
                logger.info('WLAN Cell - Set 802.11a/n standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard ANSTd")
            elif choice == standard['key6']:
                logger.info('WLAN Cell - Set 802.11g/n standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard GNSTd")
            elif choice == standard['key7']:
                logger.info('WLAN Cell - Set 802.11g(OFDM)/n standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard GONStd")
            elif choice == standard['key8']:
                logger.info('WLAN Cell - Set 802.11ac standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard ACSTd")
            elif choice == standard['key9']:
                logger.info('WLAN Cell - Set 802.11ax standard')
                cmw.write("CONFigure:WLAN:SIGN:CONNection:STANdard AXSTd")

            logger.info('{0}'.format(132 * '-'))
            logger.info('WLAN - Set WLAN Signaling  AP Output Power')
            RxExpectedpower=cmw.write("CONF:WLAN:SIGN:RFS:ANT1:EPEPower {0:5.1f}".format(wlan.Rx_expected_power))
            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('WLAN - Set WLAN Signaling AP  TX Expected Power')
            TxBurstpower=cmw.write("CONF:WLAN:SIGN:RFS:BOPower {0:5.1f}".format(wlan.Tx_Burst_power))
            logger.info('{0}'.format(132 * '-'))
            Bdw=cmw.write('CONFigure:WLAN:SIGN:RFSettings:OCWidth BW20')

            logger.info('{0}'.format(132 * '-'))

            logger.info('{0}'.format(132 * '-'))
            logger.info('WLAN - Set channel: {0}'.format(wlan.channel))
            RF_channel=cmw.write("CONF:WLAN:SIGN:RFS:CHANnel {0}".format(wlan.channel))

            logger.info('{0}'.format(132 * '-'))

            erreur = cmw.ask("SYST:ERR:ALL?")
            if erreur[0] != '0':
                 raise ValueError(erreur)



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

                    # get a socket instance for controlling CMW

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
                    #  Passing SCPI comands to FSW
                    logger.debug(132 * '-')
                    fsw.timeout = 30.0

                    # fsw.write("*CLS")
                    fsw.write("*RST")
                    fsw.write("INIT:CONT OFF")
                    fsw.write("SYST:PRES:ALL")
                    time.sleep(0.5)
                    fsw.write("SENSe:CORRection:TRANsducer:SELect 'dummy_FSW_pathloss'")
                    fsw.write("SENSe:CORRection:TRANsducer:ON")
                    fsw.write("SENSe:CORRection:TRANsducer:UNIT 'DB'")
                    fsw.write("SENSe:CORRection:TRANsducer:COMMent 'Test Transducer'")
                    fsw.write("SENSe:CORRection:TRANsducer:DATA 30e6,5, 13e9, 3")
                    time.sleep(10)
                    fsw.write("INIT:CONT ON")
                    fsw.write("INP:ATT:AUTO OFF")
                    fsw.write("INP:ATT 40")

                # Turn WLAN SIGN ON
                if 1:
                    #
                    logger.info('{0}'.format(132 * '-'))

                    logger.info('TURN WLAN Signaling ON')

                    cmw.write("SOUR:WLAN:SIGN:STATe ON")

                    TIMEOUT = 30.0
                    tstart = time.time()
                    buffin = cmw.ask("SOUR:WLAN:SIGN:STAT:ALL?")
                    while not (buffin[0] == 'ON' and buffin[1] == "ADJ"):

                        buffin = cmw.ask("SOURce:WLAN:SIGN:STAT:ALL?")
                        logger.debug("state is :{0}".format(buffin))
                        time.sleep(0.5)
                        if (time.time() - tstart) > TIMEOUT:
                            # x = win32api.MessageBox(0, "TIMEOUT occurs")
                            raise ValueError('TIMEOUT - wlan Signaling Turn OFF')


                    time.sleep(30)

                    #device.shell('svc wifi disable')
                    #time.sleep(30)
                    device.shell('svc wifi enable')
                    time.sleep(30)

                    # Retrieve connection related information
                    # Connection state?

                    state = cmw.ask("FETch:WLAN:SIGN:PSWitched:STATe?")
                    logger.debug("connection state is{0}".format(state))

                    # RX Power Indicator

                    #RX_Power = cmw.ask("SENSe:WLAN:SIGN:SINF[:ANTenna]:RXPindicator?")
                    #logger.debug("rx_power is{0}".format(RX_Power))

                    # MAC address
                    mac_address = cmw.ask('SENSe:WLAN:SIGN:UECapability:MAC:ADDRess?')
                    logger.debug("mac address is{0}".format(mac_address))
                    """
                    # IP Address
                    ip_address = cmw.query("SENSe:WLAN:SIGN:UESinfo:UEADdress:IPV?")

                    logger.debug("ip address is {0}".format(ip_address))
                    #cmw.query("SENSe:WLAN:SIGN:UESinfo:CMWaddress:IPV?")
                    #device.shell('ping -c 10 172.22.1.201')
                    """
                    #device.shell('ping -c 5 172.22.1.201')
                    # RX Statistics
                    RXbpower = cmw.ask('SENSe:WLAN:SIGN:UESinfo:RXBPower?')
                    logger.debug("RX Power is {0}".format(RXbpower))
                    """
                    Datarate = cmw.ask("SENSe:WLAN:SIGN<i>:UESinfo:DRATe?")
                    logger.debug("Data rate is {0}".format(Datarate))
                    ABSReport = cmw.ask("SENSe:WLAN:SIGN<i>:UESinfo:ABSReport?")
                    logger.debug("ABS Report is {0}".format(ABSReport))
                    
                    
                    #saveing screenshot
                    # captured area AWINdow | MWINdow | FSCReen
                    cmw.write("HCOPy:AWINdow")
                    # file type
                    cmw.write("HCOPy:DEVice:PNG")
                    # commands also save a screenshot.
                    cmw.write("HCOPy:FILE'D:\Rohde-Schwarz\CMW\Data\Print\image1'")
                    cmw.write("HCOPy:INTerior:FILE")
                    cmw.write("HCOPy:DATA?")
                    cmw.write("HCOPy:INTerior:DATA?")
                    """

                    RAT_info = 'WIFI'
                    std = sys.argv[1]


                    dict = {'STANDARD':std,'STATE':state,'MAC ADDRESS': mac_address,'RXBPOWER': RXbpower}

                    df=pd.DataFrame(dict,index=[0])
                    timestr = time.strftime("%Y%m%d-%H%M%S")

                    df.to_csv('{3}\\CMW_output_{0}_std{1}_{2}.csv'.format(RAT_info, std, timestr, mydir_d))


                    tx_mev = True

                    if tx_mev:

                        logger.debug(' WLAN TX Multi-Evaluation TEST')

                        logger.debug('Route WLAN MEV in Combine Signal Path')
                        cmw.write('ROUTe:WLAN:MEAS:SCENario:CSP "WLAN Sig1"')

                        logger.debug('Set WLAN MEV standard to 802.11g ')
                        cmw.write('CONF:WLAN:MEAS:ISIGnal:STANdard {0}'.format('LOFD'))

                        logger.debug('Set WLAN MEV Analyzer to evaluate Modulation over 20 OFDM symbols')
                        cmw.write('CONFigure:WLAN:MEAS:ISIGnal:OFDM:ELENgth 20')

                        logger.debug('Set WLAN MEV Analyzer Channel Estimation Payload')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:COMPensation:CESTimation PAYL')

                        logger.debug('Set WLAN MEV Analyzer Tracking Modulation')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:COMPensation:TRACking:PHASe ON')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:COMPensation:TRACking:TIMing ON')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:COMPensation:TRACking:LEVel OFF')

                        logger.debug('Set WLAN MEV Analyzer run in SIngle SHot Mode')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:REPetition SING')

                        logger.debug('Set WLAN MEV Analyzer Disable All Views')
                        buffin = cmw.ask('CONFigure:WLAN:MEAS:MEValuation:RESult?')
                        for index, x in enumerate(buffin):
                            if 'ON' in x:
                                buffin[index] = 'OFF'
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:RESult {0}'.format(','.join(buffin)))

                        logger.debug('Set WLAN MEV Analyzer Enable Views')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:RESult:MSCalar ON')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:RESult:TSMask ON')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:TSMask:OBWPercent ON')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:RESult:SFLatness ON')

                        logger.debug('Set WLAN MEV  Measurement Statitics Count')
                        # Mod
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:SCOunt:MODulation 5')

                        # TSM
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:SCOunt:TSMask 5')
                        cmw.write('CONFigure:WLAN:MEAS:MEValuation:SCOunt:PVTime 1')


                        logger.debug('INFO:*** ABort Multi Eval Measurement')
                        cmw.write('ABORt:WLAN:MEAS:MEValuation')

                        logger.debug('INFO:*** Turn OFF Packet Generator')
                        for index_pg in range(1, 4):
                            pg_state = cmw.ask('CONFigure:WLAN:SIGN:PGEN{0}:CONFig?'.format(index_pg))
                            if 'ON' in pg_state:
                                pg_state[0] = 'OFF'
                                pg_state = cmw.write('CONFigure:WLAN:SIGN:PGEN{0}:CONFig {1}'.format(index_pg, ','.join(pg_state)))

                        logger.debug('INFO:*** Enable Packet Generator1 to create reverse link activity')
                        cmw.write('CONFigure:WLAN:SIGN:PGEN1:PROTocol ICMp')
                        cmw.write('CONFigure:WLAN:SIGN:PGEN1:CONFig ON, 100, 1472, PRAN, TID0')

                        logger.debug('INFO:*** Enable Trigger Filter to capture OFDM 54 Mbps packets')
                        cmw.write('TRIGger:WLAN:SIGN:RX:MACFrame:BTYPe NHTBursts')
                        cmw.write('TRIGger:WLAN:SIGN:RX:MACFrame:RATE Q6M34')
                        cmw.write('TRIGger:WLAN:SIGN:RX:MACFrame:RREStriction ON')


                        logger.debug('Trig WLAN MEV')
                        #cmw.write('ABORt:WLAN:MEAS:MEValuation')
                        cmw.write('INIT:WLAN:MEAS:MEValuation')

                        logger.debug('Wait for WLAN MEV analyzer to complete the TX measurements')
                        while True:

                            time.sleep(20)
                            #device.shell('svc wifi enable')

                            Connection_state = cmw.ask('FETCh:WLAN:SIGN:PSWitched:STATe?')
                            if 'ASS' not in Connection_state:
                                raise ValueError('DUT is not in Association mode')


                            per_state = cmw.ask('FETCh:WLAN:MEAS:MEV:STATe:ALL?')
                            if per_state[0] == 'RDY' and per_state[1] == 'ADJ' and per_state[2] == 'INV':
                                logger.debug('WLAN TX MEV measurement Ready')
                                break

                        logger.debug('Get TX WLAN Scalar Modulation results')
                        buffin = cmw.ask('FETCh:WLAN:MEAS:MEValuation:MODulation:AVERage?')
                        res = ['1_RI', '2_OutOfTol', '3_MCSIndex', '4_Modulation', '5PayLoadSym',
                               '6_MeasuredSym', '7_PayloadBytes', '8_GuardInterval',
                               '9_NoSS', '10_NoSTS', '11_BurstRate', '12_PowerBackOff',
                               '13_BurstPower', '14_PeakPower', '15_CrestFactor', '16_EVMAllCarr',
                               '17_EVMDataCarr', '18_EVMPilotCarr', '19_FreqError', '20_ClockError',
                               '21_IQOffset', '22_DCPower', '23_GainImbalance', '24QuadError',
                               '25_LTFPower', '26_DataPower']
                        for i_meas, meas in enumerate(buffin):
                            if 'E+' in meas or 'E-' in meas:
                                buffin[i_meas] = '{0:8.3f}'.format(float(meas))
                            logger.debug('{0}:{1:>8}'.format(res[i_meas], buffin[i_meas]))

                        logger.debug('Get TX WLAN TSM results')
                        buffin = cmw.ask('FETCh:WLAN:MEAS:MEValuation:TSMask:AVERage?')
                        res = ['1_RI', '2_OutOfTol', '3_AB', '4_BC', '5_CD', '6_DE', '7_ED', '8_DC', '9_CB', '10_BA']
                        for i_meas, meas in enumerate(buffin):
                            if 'E+' in meas or 'E-' in meas:
                                buffin[i_meas] = '{0:8.3f}'.format(float(meas))
                            logger.debug('{0}:{1:>8}'.format(res[i_meas], buffin[i_meas]))

                        logger.debug('Get TX WLAN OBW results')
                        buffin = cmw.ask('FETCh:WLAN:MEAS:MEValuation:TSMask:OBW?')
                        res = ['1_RI', '2_OBW_cur', '3_OBW_avg', '4_OBW_max', '5_OBW_sdev', '6_OBW_left', '7_OBW_right']
                        for i_meas, meas in enumerate(buffin):
                            if 'E+' in meas or 'E-' in meas:
                                buffin[i_meas] = '{0:8.3f}'.format(float(meas))
                            logger.debug('{0}:{1:>8}'.format(res[i_meas], buffin[i_meas]))



            fsw.write("SWE:MODE LIST")
            logger.info('{0}'.format(132 * '-'))
            logger.info('SCPI commands for FSW')
            logger.info('{0}'.format(132 * '-'))
            fsw.write("INIT:CONT OFF")
            fsw.write("LIST:RANG:COUNt?")

            #fsw.write("LIST:RANG:DEL")
            fsw.write("SENS:LIST:RANG1:DEL")
            fsw.write("SENS:LIST:RANG1:DEL")
            fsw.write("SENS:LIST:RANG1:DEL")
            #fsw.write("SENS:LIST:RANG3:DEL")

            # range
            count = 1
            for (strt, stp, rbw, vbw, swp, lmt) in zip(freq_start, freq_stop, rbw_in, vbw_in, sweep_point_value, limit):
                fsw.write("LIST:RANG{0}:STAR {1}".format(count, strt))  # fsw.write("LIST:RANG1:STAR 3000000000")
                fsw.write("LIST:RANG{0}:STOP {1}".format(count, stp))
                fsw.write("LIST:RANG{0}:BAND {1}".format(count, rbw))
                fsw.write("LIST:RANG{0}:BAND:VID {1}".format(count, vbw))
                fsw.write("LIST:RANG{0}:INP:ATT:AUTO OFF".format(count))
                fsw.write("LIST:RANG{0}:INP:ATT {1}".format(count, att_rf))
                # fsw.write("LIST:RANG1:FILT:TYPE CFILter")
                fsw.write("LIST:RANG{0}:DET {1}".format(count, str(detector_type)))
                fsw.write("LIST:RANG{0}:POIN {1}".format(count, swp))
                fsw.write("LIST:RANG{0}:RLEV {1}".format(count, ref_lev))
                fsw.write("SENS:LIST:RANG:TRAN 'dummy_FSW_pathloss'")
                fsw.write("LIST:RANG{0}:SWE:TIME {1}".format(count, sweep_time))
                fsw.write("LIST:RANG{0}:LIM:STAR {1}".format(count, lmt))
                fsw.write("LIST:RANG{0}:LIM:STOP {1}".format(count, lmt))

                fsw.write(132 * '-')

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

            #fsw.write("MMEM:STOR1:TRAC 1,'C:\\R_S\\instr\\user\\fsw_Results_{0}.CSV'".format(row_count))
            logger.debug(len(list_of_Freq))
            logger.debug(list_of_Freq)


            if len(list_of_Freq) == 3:

                #list_of_Freq= ['+2.489990937E+005', '-4.296238327E+001', '-6.962383270']
                #min = -30.0
                max = -36.0
                verdict = []
                if float(list_of_Freq[1])< float(max):
                    summary = 'PASS'
                else:
                    summary = 'FAIL'
                #abs_fre = [Meas[1][0]]
                logger.debug("abs power msw value are {0}".format(float(list_of_Freq[1])))
                # Measured values of ranges 1,2,3 should be less than -36 dbm
                #logger.debug(abs_fre)
                #logger.debug(len(abs_fre))

                if float(list_of_Freq[1]) <= float(max):
                    print("abs _power {0}".format(float(list_of_Freq[1])))
                    verdict.append('PASS')

                # print("for max values of 1 to3 ranges", verdict)
                else:
                    print("abs _power {0}".format(float(list_of_Freq[1])))
                    verdict.append('FAIL')
                    print("for max values of range1", verdict[0])

                #RAT_info = 'WIFI'
                #standard = '802_11g'
                #logger.debug("verdict list is : ", verdict)
                #logger.debug(Meas)
                logger.debug(132 * '-')
                logger.debug("Measurement Ranges for FSW spectrum analyzer")
                logger.debug(132 * '-')
                logger.debug(" Range  | Freq  kHZ| PowerAbs(-dbm) |  limit (-db) | Verdict  ")
                logger.debug(" Range1 | {0:.05f}     | {1:.02f} |  {2:.02f} |{3}  ".format(float(list_of_Freq[0]) / 1000,float(list_of_Freq[1]),
                                                                                      float(list_of_Freq[2]),
                                                                                      verdict[0]))

                logger.debug(132 * '-')
                logger.debug(" Test Summary for Frequency Measurement for all ranges : {0}  ".format(summary))
                logger.debug(132 * '-')
                """
                dict = {'STANDARD': std, 'BANDWIDTH': Bdw, 'RFCHANNEL': RF_channel, 'TXBURSTPOWER': TxBurstpower,
                        'RXEXPECTEDPOWER': RxExpectedpower,'STATE': state,
                        'MAC ADDRESS': mac_address,'RXBurstPower': RXbpower,'SUMMARY': summary}

                df = pd.DataFrame(dict)
                timestr = time.strftime("%Y%m%d-%H%M%S")

                df.to_csv('{3}\\cmw_logsresult_{0}_std{1}_{2}.csv'.format(RAT_info, std, timestr, mydir_d),
                          index=False)
                """
                 # writing to file Fsw measuremnt
                ranges = [1]


                # dictionary of lists

                dict = {'RAT': RAT_info, 'IEEE STANDARD':standard, 'Range': ranges, 'RBW': rbw_in, 'frequency': float(list_of_Freq[0]),
                            'abs_power': float(list_of_Freq[1]), 'limit_pwr': float(list_of_Freq[2]),'PASS/FAIL':verdict }

                df = pd.DataFrame(dict)
                timestr = time.strftime("%Y%m%d-%H%M%S")
                    # saving the dataframe
                logger.debug(132 * '_')
                logger.debug(mydir_d)
                logger.debug(132 * '_')
                #logger.debug(df)
                df.to_csv('{3}\\fsw_logsresult_{0}_band{1}_{2}.csv'.format(RAT_info, standard , timestr, mydir_d),
                              index=False,
                              mode='a')


                    # dictionary of lists

            else:
                logger.debug(" fsw intialization fail or either FSW spurious msmt  values are 1 or 0 ")
                logger.debug("FSW scpi command fsw.ask(TRAC:DATA? SPURIOUS) returns either value 1  or 0 in msmt list ")

            logger.debug(132 * '_')
            logger.debug(132 * '_')
            # End Init FSW
        logger.info('{0}'.format(132 * '-'))

        """
        if erreur[0] != '0':
            raise ValueError(erreur)
        logger.info('{0}'.format(132 * '-'))
        """
        logger.debug("at the start of screenshot");
        rth = RsInstrument('TCPIP::192.168.0.219::INSTR')
        rm = pyvisa.ResourceManager()
        instr = rm.open_resource('TCPIP::192.168.0.219::INSTR')  # replace by your IP-address
        instr.timeout = 3000
        logger.debug("at the middle of screenshot");
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
        timestr_fsw = time.strftime("%Y%m%d-%H%M%S")
        filePathInstr = r"/temp/spurious_emi{0}_{1}_{2}.png".format(RAT_info, standard, timestr_fsw)  # size of 18kb
        filePathPc = r"{3}\\spurious_emi{0}_{1}_{2}.png".format(RAT_info, standard, timestr_fsw, mydir_d)  # no data


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
        logger.debug("at the end of screenshot");
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

#logger.debug("end of {0} th loop".format(int(row_count)))

# end of While loop
# Storing all csv file in to single file to conclude the results summary for all runs
timestr_out = time.strftime("%Y%m%d")
logger.debug(132 * '_')
logger.debug(mydir_d)
logger.debug(132 * '_')
# defining glob function to aggregate the CMW, FSW CSV files
logger.debug(132 * '_')

cmw_csv_files = glob("{1}\\CMW_*.csv".format(timestr_out, mydir_d))
#creating pandas data frame dict for cmw csv files
df = pd.concat((pd.read_csv(f, header = 0) for f in cmw_csv_files))
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

        all_csv_files = glob(os.path.join(self._path, "FSW_verdict_*.csv"))
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

