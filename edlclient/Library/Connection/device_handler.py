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
        time_out (int): USB通信默认超时时间（毫秒），默认值1000
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
        """ 受控打印方法，根据enabled_print状态决定是否输出内容。

        Args:
            *objects: 待打印的任意数量对象（可变位置参数）
            sep (str): 多对象间的分隔符，默认值为单个空格
            end (str): 打印结束时追加的字符串，默认值为换行符
            file (_io.TextIOWrapper): 输出流对象，默认值为标准输出（sys.stdout）
            flush (bool): 是否强制刷新输出缓冲区，默认值为False

        说明:
            仅当实例的enabled_print属性为True时，才会调用内置print函数输出内容
            
        """
        if self.enabled_print:
            print(*objects, sep, end, file, flush)
    
    def read(self, length: int | None = None, timeout: int = -1) -> bytes:
        """ 通用数据读取方法，封装底层usb_read实现统一读取接口。

        Args:
            length (int | None): 读取字节数，为None时使用maxsize默认值
            timeout (int): 读取超时时间（毫秒），-1时使用实例timeout默认值

        Returns:
            bytes: 从设备读取的二进制数据
            
        """
        if timeout == -1:
            timeout = self.timeout
        if length is None:
            length = self.maxsize
        
        return self.usb_read(length, timeout) # TODO: 该方法似乎没实现
    
    def read_dword(self, count: int = 1, little: bool = False) -> int | tuple[int]:
        """ 读取指定数量的DWORD（4字节）数据，支持大小端格式。

        Args:
            count (int): 读取的DWORD数量，默认值1
            little (bool): 是否使用小端序解析，False为大端序，默认值False

        Returns:
            int | tuple[int]: 单条数据返回int，多条返回tuple
            
        """
        rev = "<" if little else ">"
        value = self.usb_read(4 * count) # TODO: 该方法似乎未实现
        data = unpack(rev + "I" * count, value)
        
        if count == 1:
            return data[0]
        return data
    
    def read_word(self, count: int = 1, little: bool = False) -> int | list[int]:
        """ 读取指定数量的WORD（2字节）数据，支持大小端格式。

        Args:
            count (int): 读取的WORD数量，默认值1
            little (bool): 是否使用小端序解析，False为大端序，默认值False

        Returns:
            int | list[int]: 单条数据返回int，多条返回list；读取空数据时返回空列表
            
        """
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
    
    def read_byte(self, count: int = 1) -> bytes:
        """ 读取指定数量的字节数据。

        Args:
            count (int): 读取的字节数，默认值1

        Returns:
            bytes: 读取的二进制字节数据
            
        """
        return self.usb_read(count)
    
    def verify_data(self, data: bytes | bytearray | str, pre: str = 'RX:') -> bytes | None:
        """ 数据校验与日志输出方法，格式化输出二进制/XML数据至日志。

        Args:
            data (bytes | bytearray | str): 待校验/输出的数据
            pre (str): 日志前缀标识，默认值'RX:'

        Returns:
            bytes | None: 处理后的XML数据（若输入为XML格式），否则返回原数据

        说明:
            1. DEBUG级别下会输出调用栈信息（排除自身与Port类相关栈帧）
            2. XML格式数据尝试按行解码输出，非XML二进制数据以16进制输出
            3. 解码失败时自动降级为16进制格式输出
            
        """
        if self._logger.level == logging.DEBUG:
            frame = inspect.currentframe()
            stack_trace = traceback.format_stack(frame)
            td = []
            for trace in stack_trace:
                if 'verify_data' not in trace and 'Port' not in trace:
                    td.append(trace)
            self.debug(td[:-1])
        
        if isinstance(data, bytes) or isinstance(data, bytearray):
            if data[:5] == b'<?xml':
                try:
                    rdata = b''
                    for line in data.split(b'\n'):
                        try:
                            self.debug(pre + line.decode('utf-8'))
                            rdata += line + b"\n"
                        except UnicodeDecodeError:
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
                self.debug(pre + hexlify(data.encode('utf-8')).decode('utf-8'))
                
        return data
    
    @abc.abstractmethod
    def connect(self, port_name: str = '') -> bool:
        """ 抽象方法：建立与设备的连接。

        Args:
            port_name (str, optional): 设备端口名（如COM3、/dev/ttyUSB0），默认空字符串

        Returns:
            bool: 连接成功返回True，失败返回False

        子类实现要求:
            1. 需处理端口不存在、权限不足、设备未响应等异常场景
            2. 成功连接后需将connected属性设为True
            
        """
        pass
    
    @abc.abstractmethod
    def close(self, reset: bool = False):
        """ 抽象方法：关闭设备连接。

        Args:
            reset (bool): 是否在关闭连接时重置设备，默认值False

        子类实现要求:
            1. 需释放设备句柄和系统资源
            2. 关闭后需将connected属性设为False
            3. 重置参数为True时，需执行设备硬件重置操作
            
        """
        pass
    
    @abc.abstractmethod
    def flush(self):
        """ 抽象方法：刷新设备输入/输出缓冲区。

        子类实现要求:
            需清空底层通信接口的接收和发送缓冲区，确保无残留数据
            
        """
        pass
    
    @abc.abstractmethod
    def detect_devices(self):
        """ 抽象方法：检测可用设备列表。

        Returns:
            list: 包含可用设备信息的列表（如[(vid, pid, port), ...]）

        子类实现要求:
            需扫描系统中匹配的USB/串口设备，返回标准化的设备信息
            
        """
        pass
    
    @abc.abstractmethod
    def get_interface_count(self) -> int:
        """ 抽象方法：获取设备可用接口数量。

        Returns:
            int: 设备支持的通信接口数量
            
        """
        pass
    
    @abc.abstractmethod
    def set_line_coding(self, baud_rate: int | None = None, parity: int = 0, databits: int = 8, stop_bits: int = 1):
        """ 抽象方法：配置串口通信参数。

        Args:
            baud_rate (int | None): 波特率，为None时使用实例baudrate属性值
            parity (int): 校验位配置（0=无校验，1=奇校验，2=偶校验），默认值0
            databits (int): 数据位数量（5/6/7/8），默认值8
            stop_bits (int): 停止位数量（1/1.5/2），默认值1

        子类实现要求:
            需将配置参数同步至实例属性和底层硬件
            
        """
        pass
    
    @abc.abstractmethod
    def set_break(self):
        """ 抽象方法：设置串口中断状态。

        子类实现要求:
            需触发硬件级别的串口Break信号，持续时间符合行业标准
            
        """
        pass
        
    @abc.abstractmethod
    def set_control_line_state(self, RTS: int | None = None, DTR: int = None, isFTDI: bool = False):
        """ 抽象方法：设置串口控制线状态。

        Args:
            RTS (int | None): RTS（请求发送）线状态，None表示不修改
            DTR (int | None): DTR（数据终端就绪）线状态，None表示不修改
            isFTDI (bool): 是否为FTDI芯片设备，默认值False

        子类实现要求:
            1. 仅修改非None的控制线状态
            2. FTDI设备需适配专属的控制线操作逻辑
            
        """
        pass
    
    @abc.abstractmethod
    def write(self, command: bytes, data_pack_size: int | None = None):
        """ 抽象方法：发送数据至设备（高层封装）。

        Args:
            command (bytes): 待发送的二进制数据
            data_pack_size (int | None): 数据包大小，None时使用默认分包策略

        Returns:
            int: 实际发送的字节数

        子类实现要求:
            需封装usb_write方法，实现数据分包、校验等高层逻辑
            
        """
        pass
    
    @abc.abstractmethod
    def usb_write(self, data: bytes, data_pack_size: int | None = None) -> int:
        """ 抽象方法：底层USB数据发送。

        Args:
            data (bytes): 待发送的原始二进制数据
            data_pack_size (int | None): 单次发送的数据包大小，None使用设备默认值

        Returns:
            int: 实际发送的字节数

        子类实现要求:
            需直接操作USB底层接口，处理发送超时、总线错误等异常
            
        """
        pass
    
    @abc.abstractmethod
    def usb_read(self, resp_len: int | None = None, timeout: int = 0):
        """ 抽象方法：底层USB数据读取。

        Args:
            resp_len (int | None): 期望读取的字节数，None使用maxsize默认值
            timeout (int): 读取超时时间（毫秒），0表示无限等待

        Returns:
            bytes: 从USB接口读取的二进制数据

        子类实现要求:
            需处理读取超时、数据截断、总线断开等异常场景
            
        """
        pass
    
    @abc.abstractmethod
    def ctrl_transfer(self, request_type: int, request: int, value: int,
                      index: int, data_or_length: bytes | int) -> bytes | int:
        """ 抽象方法：执行USB控制传输。

        Args:
            request_type (int): USB请求类型（方向、类型、接收者）
            request (int): USB请求码
            value (int): 请求参数值
            index (int): 请求索引值
            data_or_length (bytes | int): 发送的数据（OUT请求）或接收长度（IN请求）

        Returns:
            bytes | int: IN请求返回读取的数据，OUT请求返回发送的字节数

        子类实现要求:
            需严格遵循USB 2.0/3.0规范实现控制传输逻辑
            
        """
        pass
    
    @abc.abstractmethod
    def usb_read_write(self, data: bytes, resp_len: int) -> bytes:
        """ 抽象方法：USB读写一体化操作（发送数据并立即读取响应）。

        Args:
            data (bytes): 待发送的请求数据
            resp_len (int): 期望读取的响应字节数

        Returns:
            bytes: 设备返回的响应数据

        """
        pass
    