#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!
import logging
import sys
from struct import unpack
import os
import abc

import inspect
import traceback
from binascii import hexlify

from edlclient.Library.gpt import LogBase
from edlclient.Tools import null


class DeviceClass(abc.ABC, metaclass=LogBase):
    """
    代表一个设备类，用于与特定类型的硬件设备进行交互。
    该类提供了一系列的方法来控制和与设备通信。
    
    """

    def __init__(self, log_level: int = logging.INFO, port_config = None, dev_class: int = -1,
                 enabled_log: bool = False, enabled_print: bool = False):
        """
        初始化一个新的DeviceClass实例。

        Args:
            log_level (int): 日志级别，默认为logging.INFO。
            port_config: 端口配置。
            dev_class (int): 设备类别。
            enabled_log (bool): 是否开启日志功能
            enabled_print (bool): 是否开启输出功能
            
        """
        self.connected = False
        self.timeout = 1000
        self.maxsize = 512
        self.vid = None
        self.pid = None
        self.stop_bits = None
        self.databits = None
        self.parity = None
        self.baudrate = None
        self.configuration = None
        self.device = None
        self.dev_class = dev_class
        self.loglevel = log_level
        self.xml_read = True
        self.port_config = port_config
        self.enabled_print = enabled_print
        self.enabled_log = enabled_log
        
        if self.enabled_log:
            self._logger = self._logger
            self.info = self._logger.info
            self.error = self._logger.error
            self.warning = self._logger.warning
            self.debug = self._logger.debug
            self._logger.setLevel(log_level)
            if log_level == logging.DEBUG:
                log_file_name = os.path.join("logs", "log.txt")
                fh = logging.FileHandler(log_file_name, encoding='utf-8')
                self._logger.addHandler(fh)
        else:
            self._logging = null.null_function
            self.info = null.null_function
            self.error = null.null_function
            self.warning = null.null_function
            self.debug = null.null_function
    
    def _print(self, *objects, sep: str = ' ', end: str = '\n', file = sys.stdout, flush: bool = False):
        """ 自定义打印方法，根据enabled_print来决定是否打印
        
        Args:
            *object: 待打印的对象（可变位置参数）
            sep (str): 多个对象之间的分隔符，默认为 ' ' (一个空格)
            end (str): 打印结束时追加的字符串，默认为 '\n'
            file (_io.TextIOWrapper): 输出流对象（文件句柄），默认为 sys.stdout
            flush (bool): 是否强制刷新输出缓冲区，默认为 False (关闭)
            
        """
        if self.enabled_print:
            print(*objects, sep, end, file, flush)
    
    @abc.abstractmethod
    def connect(self, port_name: str = '') -> bool:
        """
        连接到设备。

        Args:
            port_name (str, optional): 串口端口名（如COM3、/dev/ttyUSB0），默认空字符串

        Returns:
            bool: 连接成功返回True，失败返回False

        """
        pass

    def close(self, reset=False):
        raise NotImplementedError()

    def flush(self):
        raise NotImplementedError()

    def detect_devices(self):
        raise NotImplementedError()

    def getInterfaceCount(self):
        raise NotImplementedError()

    def set_line_coding(self, baudrate=None, parity=0, databits=8, stopbits=1):
        raise NotImplementedError()

    def setbreak(self):
        raise NotImplementedError()

    def setcontrollinestate(self, RTS=None, DTR=None, isFTDI=False):
        raise NotImplementedError()

    def write(self, command, pktsize=None):
        raise NotImplementedError()

    def usbwrite(self, data, pktsize=None):
        raise NotImplementedError()

    def usbread(self, resplen=None, timeout=0):
        raise NotImplementedError()

    def ctrl_transfer(self, bmRequestType, bRequest, wValue, wIndex, data_or_wLength):
        raise NotImplementedError()

    def usbreadwrite(self, data, resplen):
        raise NotImplementedError()

    def read(self, length=None, timeout=-1):
        if timeout == -1:
            timeout = self.timeout
        if length is None:
            length = self.maxsize
        return self.usbread(length, timeout)

    def rdword(self, count=1, little=False):
        rev = "<" if little else ">"
        value = self.usbread(4 * count)
        data = unpack(rev + "I" * count, value)
        if count == 1:
            return data[0]
        return data

    def rword(self, count=1, little=False):
        rev = "<" if little else ">"
        data = []
        for _ in range(count):
            v = self.usbread(2)
            if len(v) == 0:
                return data
            data.append(unpack(rev + "H", v)[0])
        if count == 1:
            return data[0]
        return data

    def rbyte(self, count=1):
        return self.usbread(count)

    def verify_data(self, data, pre="RX:"):
        if self._logger.level == logging.DEBUG:
            frame = inspect.currentframe()
            stack_trace = traceback.format_stack(frame)
            td = []
            for trace in stack_trace:
                if "verify_data" not in trace and "Port" not in trace:
                    td.append(trace)
            self.debug(td[:-1])

        if isinstance(data, bytes) or isinstance(data, bytearray):
            if data[:5] == b"<?xml":
                try:
                    rdata = b""
                    for line in data.split(b"\n"):
                        try:
                            self.debug(pre + line.decode('utf-8'))
                            rdata += line + b"\n"
                        except:
                            v = hexlify(line)
                            self.debug(pre + v.decode('utf-8'))
                    return rdata
                except Exception as err:
                    self.debug(str(err))
                    pass
            if logging.DEBUG >= self._logger.level:
                self.debug(pre + hexlify(data).decode('utf-8'))
        else:
            if logging.DEBUG >= self._logger.level:
                self.debug(pre + hexlify(data).decode('utf-8'))
        return data
