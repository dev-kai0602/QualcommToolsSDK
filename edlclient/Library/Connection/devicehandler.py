#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!
from binascii import hexlify
from struct import unpack
import traceback
import logging
import sys
import os
import abc

import inspect

from edlclient.Library.gpt import LogBase
from edlclient.Tools import null


class DeviceClass(abc.ABC, metaclass=LogBase):
    """抽象设备交互基类，定义硬件设备通信的标准化接口。

    该类为特定类型硬件设备（如USB串口设备）的交互提供统一抽象层，包含设备连接、
    数据读写、参数配置、日志输出等核心能力的抽象定义与基础实现。子类需实现所有
    抽象方法以适配具体设备的通信逻辑。

    Attribute:
        connected (bool): 设备连接状态标识，True表示已连接
        timeout (int): USB通信默认超时时间（毫秒），默认值1000
        maxsize (int): 默认最大单次读取字节数，默认值512
        vid (int | None): USB设备厂商ID
        pid (int | None): USB设备产品ID
        stop_bits (int | None): 串口停止位数量（1/1.5/2）
        databits (int | None): 串口数据位数量（5/6/7/8）
        parity (int | None): 串口校验位配置（0=无校验，1=奇校验，2=偶校验）
        baud_rate (int | None): 串口波特率（bps）
        configuration (int | None): USB设备配置值
        device (object | None): 底层设备操作句柄
        dev_class (int): 自定义设备分类标识，默认值-1
        loglevel (int): 日志输出级别（参考logging模块常量）
        xml_read (bool): XML格式数据解析开关，默认开启（True）
        port_config (dict | None): 设备端口配置参数（设备专属）
        enabled_print (bool): 控制台输出开关，默认关闭（False）
        enabled_log (bool): 日志记录开关，默认关闭（False）
        
    """

    def __init__(self, log_level: int = logging.INFO, port_config = None, dev_class: int = -1,
                 enabled_log: bool = False, enabled_print: bool = False):
        """ 初始化设备类实例，配置日志与通信基础参数。

        Args:
            log_level (int): 日志输出级别，默认值logging.INFO
            port_config (dict | None): 设备端口配置字典（如串口参数、USB端点配置等）
            dev_class (int): 自定义设备分类标识，用于区分不同设备类型，默认值-1
            enabled_log (bool): 是否启用日志记录功能，默认关闭
            enabled_print (bool): 是否启用控制台打印功能，默认关闭

        说明:
            1. 启用日志后，DEBUG级别日志会输出至 logs/log.txt 文件
            2. 未启用日志时，所有日志方法（info/error/warning/debug）会绑定空函数
            3. 控制台输出功能由自定义_print方法实现，受enabled_print控制
            
        """
        self.connected = False
        self.timeout = 1000
        self.maxsize = 512
        self.vid = None
        self.pid = None
        self.stop_bits = None
        self.databits = None
        self.parity = None
        self.baud_rate = None
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
    
    def read(self, length=None, timeout=-1):
        if timeout == -1:
            timeout = self.timeout
        if length is None:
            length = self.maxsize
        
        return self.usb_read(length, timeout)
    
    def rdword(self, count=1, little=False):
        rev = "<" if little else ">"
        value = self.usb_read(4 * count)
        data = unpack(rev + "I" * count, value)
        if count == 1:
            return data[0]
        return data
    
    def rword(self, count=1, little=False):
        rev = "<" if little else ">"
        data = []
        for _ in range(count):
            v = self.usb_read(2)
            if len(v) == 0:
                return data
            data.append(unpack(rev + "H", v)[0])
        if count == 1:
            return data[0]
        return data
    
    def rbyte(self, count=1):
        return self.usb_read(count)
    
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
    
    @abc.abstractmethod
    def close(self, reset=False):
        pass
    
    @abc.abstractmethod
    def flush(self):
        pass
    
    @abc.abstractmethod
    def detect_devices(self):
        pass
    
    @abc.abstractmethod
    def getInterfaceCount(self):
        pass
    
    @abc.abstractmethod
    def set_line_coding(self, baudrate=None, parity=0, databits=8, stopbits=1):
        pass
    
    @abc.abstractmethod
    def set_break(self):
        pass
        
    @abc.abstractmethod
    def setcontrollinestate(self, RTS=None, DTR=None, isFTDI=False):
        pass
    
    @abc.abstractmethod
    def write(self, command, pktsize=None):
        pass
    
    @abc.abstractmethod
    def usb_write(self, data, pktsize=None):
        pass
    
    @abc.abstractmethod
    def usb_read(self, resplen=None, timeout=0):
        pass
    
    @abc.abstractmethod
    def ctrl_transfer(self, bmRequestType, bRequest, wValue, wIndex, data_or_wLength):
        pass
    
    @abc.abstractmethod
    def usbreadwrite(self, data, resplen): # TODO: What`s this?
        pass
    