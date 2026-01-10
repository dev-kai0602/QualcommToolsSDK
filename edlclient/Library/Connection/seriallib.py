#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!
import sys
import logging
# 跨平台串口缓冲区刷新适配（类Unix系统需termios）
if not sys.platform.startswith('win32'):
    import termios

import serial
import serial.tools.list_ports
import inspect

from edlclient.Library.utils import *
from edlclient.Library.Connection.devicehandler import DeviceClass


def _reset_input_buffer():
    """ 空实现的串口输入缓冲区重置函数（临时替换用）.

    用于连接串口时临时覆盖pyserial的_reset_input_buffer方法，规避系统兼容性问题。
    
    """
    pass


def _reset_input_buffer_org(self):
    """ 类Unix系统原生的串口输入缓冲区重置实现.

    Args:
        self: serial.Serial实例对象
        
    """
    if not sys.platform.startswith('win32'):
        termios.tcflush(self.fd, termios.TCIFLUSH)


class SerialDevice(DeviceClass):
    """ 串口通信设备类，继承自DeviceClass，实现跨平台串口通信核心逻辑.

    支持串口连接管理、设备自动检测、串口参数配置、数据读写、控制线操作等功能，
    兼容Windows/类Unix系统，适配指定VID/PID的USB串口设备。

    Attributes:
        is_serial (bool): 标记当前设备类型为串口设备
        device (serial.Serial): pyserial串口实例对象
        connected (bool): 串口连接状态标识
        log_level (int): 日志级别（如logging.INFO/logging.DEBUG）
        port_config (list): 串口设备VID/PID配置列表，格式[(vid1, pid1), (vid2, pid2)]
        dev_class (int): 设备类型标识
        xml_read (bool): 是否启用XML格式数据特殊解析模式
        timeout (int): 默认读写超时时间（秒）
        
    """
    
    def __init__(self, log_level: int = logging.INFO, port_config = None, dev_class: int =-1,
                 enabled_log: bool = False, enabled_print: bool = False):
        """ 初始化SerialClass实例.

        Args:
            log_level (int, optional): 日志级别，默认logging.INFO
            port_config (list, optional): 串口设备VID/PID配置列表，默认None
            dev_class (int, optional): 设备类型标识，默认-1
            enabled_log (bool, optional): 是否启用日志功能, 默认为False(不开启)
            enabled_print (bool, optional): 是否启用输出功能，默认为False(不开启)
            
        """
        super().__init__(log_level, port_config, dev_class, enabled_log, enabled_print)
        self.is_serial: bool = True

    def connect(self, port_name: str = ""):
        """ 建立串口连接.

        若未指定端口名，自动检测匹配VID/PID的串口设备；已连接时先关闭旧连接。
        串口参数默认配置：波特率115200、8位数据位、无校验、1位停止位、超时50秒。

        Args:
            port_name (str, optional): 串口端口名（如COM3、/dev/ttyUSB0），默认空字符串

        Returns:
            bool: 连接成功返回True，失败返回False
            
        """
        if self.connected:
            self.close()
            self.connected = False
            
        if port_name == "":
            devices = self.detect_devices()
            if len(devices) > 0:
                port_name = devices[0]
            else:
                return False
                
        if port_name != "":
            self.device = serial.Serial(baudrate=115200, bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                        timeout=50, xonxoff=False, dsrdtr=True, rtscts=True)
            self.device._reset_input_buffer = _reset_input_buffer
            self.device.setPort(port=port_name)
            self.device.open()
            self.device._reset_input_buffer = _reset_input_buffer_org
            self.connected = self.device.is_open
            if self.connected:
                return True
            
        return False

    def close(self, reset=False):
        """ 关闭串口连接.

        Args:
            reset (bool, optional): 重置标记（未使用），默认False
            
        """
        if self.connected:
            self.device.close()
            del self.device
            self.connected = False

    def detect_devices(self):
        """ 检测系统中匹配VID/PID的串口设备.

        遍历所有可用串口，筛选出port_config中指定VID/PID的设备，返回排序后的端口名列表。

        Returns:
            list: 匹配的串口端口名列表（如['/dev/ttyUSB0', '/dev/ttyUSB1']）
            
        """
        ids = []
        for port in serial.tools.list_ports.comports():
            for usbid in self.port_config:
                if port.pid == usbid[1] and port.vid == usbid[0]:
                    port_id = port.location[-1:]
                    print(f"Detected {hex(port.vid)}:{hex(port.pid)} device at: " + port.device)
                    ids.append(port.device)
        return sorted(ids)

    def set_line_coding(self, baud_rate=None, parity=0, databits=8, stop_bits=1):
        self.device.baudrate = baud_rate
        self.device.parity = parity
        self.device.stopbbits = stop_bits
        self.device.bytesize = databits
        self.debug("Linecoding set")

    def set_break(self):
        self.device.send_break()
        self.debug("Break set")

    def set_control_line_state(self, RTS=None, DTR=None, isFTDI=False):
        if RTS == 1:
            self.device.setRTS(RTS)
        if DTR == 1:
            self.device.setDTR(DTR)
        self.debug("Linecoding set")

    def write(self, command, data_pack_size=None):
        if data_pack_size is None:
            data_pack_size = 512
        if isinstance(command, str):
            command = bytes(command, 'utf-8')
        pos = 0
        if command == b'':
            try:
                self.device.write(b'')
            except Exception as err:
                error = str(err.strerror)
                if "timeout" in error:
                    # time.sleep(0.01)
                    try:
                        self.device.write(b'')
                    except Exception as err:
                        self.debug(str(err))
                        return False
                return True
        else:
            i = 0
            while pos < len(command):
                try:
                    ctr = self.device.write(command[pos:pos + data_pack_size])
                    if ctr <= 0:
                        self.info(ctr)
                    pos += data_pack_size
                except Exception as err:
                    self.debug(str(err))
                    # print("Error while writing")
                    # time.sleep(0.01)
                    i += 1
                    if i == 3:
                        return False
                    pass
        self.verify_data(bytearray(command), "TX:")
        self.device.flushOutput()
        timeout = 0
        time.sleep(0.005)
        """
        while self.device.in_waiting == 0:
            time.sleep(0.005)
            timeout+=1
            if timeout==10:
                break
        """
        return True

    def read(self, length=None, timeout=-1):
        if timeout == -1:
            timeout = self.timeout
        if length is None:
            length = self.device.in_waiting
            if length == 0:
                return b""
        if self.xml_read:
            if length > self.device.in_waiting:
                length = self.device.in_waiting
        return self.usb_read(length, timeout)

    def flush(self):
        return self.device.flush()

    def usb_read(self, resp_len=None, timeout=0):
        if resp_len is None:
            resp_len = self.device.in_waiting
        if resp_len <= 0:
            self.info("Warning !")
        res = bytearray()
        loglevel = self.loglevel
        self.device.timeout = timeout
        epr = self.device.read
        extend = res.extend
        if self.xml_read:
            info = self.device.read(6)
            bytestoread = resp_len - len(info)
            extend(info)
            if b"<?xml " in info:
                while b"response " not in res or res[-7:] != b"</data>":
                    extend(epr(1))
                return res
        bytestoread = resp_len
        while len(res) < bytestoread:
            try:
                val = epr(bytestoread)
                if len(val) == 0:
                    break
                extend(val)
            except Exception as e:
                error = str(e)
                if "timed out" in error:
                    if timeout is None:
                        return b""
                    self.debug("Timed out")
                    if timeout == 10:
                        return b""
                    timeout += 1
                    pass
                elif "Overflow" in error:
                    self.error("USB Overflow")
                    return b""
                else:
                    self.info(repr(e))
                    return b""

        if loglevel == logging.DEBUG:
            self.debug(inspect.currentframe().f_back.f_code.co_name + ":" + hex(resp_len))
            if self.loglevel == logging.DEBUG:
                self.verify_data(res[:resp_len], "RX:")
        return res[:resp_len]

    def usb_write(self, data, data_pack_size=None):
        if data_pack_size is None:
            data_pack_size = len(data)
        res = self.write(data, data_pack_size)
        self.device.flush()
        return res

    def usb_read_write(self, data, resp_len):
        self.usb_write(data)  # size
        self.device.flush()
        res = self.usb_read(resp_len)
        return res
