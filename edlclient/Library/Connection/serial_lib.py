#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!
import sys
# 跨平台串口缓冲区刷新适配（类Unix系统需termios）
if not sys.platform.startswith('win32'):
    import termios

import serial
import serial.tools.list_ports
import inspect

from edlclient.Library.utils import *
from edlclient.Library.Connection.device_handler import DeviceClass


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
            # self.device.setPort(port=port_name)
            self.device.port = port_name
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
                    # port_id = port.location[-1:]
                    print(f"Detected {hex(port.vid)}:{hex(port.pid)} device at: " + port.device)
                    ids.append(port.device)
        return sorted(ids)

    def set_line_coding(self, baud_rate: int | None = None, parity: int = 0, databits: int = 8, stop_bits: int = 1):
        """ 配置串口通信参数（波特率、校验位、数据位、停止位

        Args:
            baud_rate (int, optional): 波特率（如9600、115200），默认None
            parity (int, optional): 校验位（0=无校验，1=奇校验，2=偶校验），默认0
            databits (int, optional): 数据位（常见8），默认8
            stop_bits (int, optional): 停止位（常见1），默认1
            
        """
        self.device.baudrate = baud_rate
        self.device.parity = parity
        self.device.stopbbits = stop_bits
        self.device.bytesize = databits
        self.debug("Line coding set")

    def set_break(self):
        """ 发送串口中断信号（Break）.

        调用pyserial的send_break()方法实现，用于触发串口设备的中断逻辑。
        
        """
        self.device.send_break()
        self.debug("Break set")

    def set_control_line_state(self, RTS: int | None = None, DTR: int | None = None, isFTDI: bool = False):
        """ 设置串口控制线状态（RTS/DTR）.

        仅处理RTS/DTR置1的场景，置0操作需扩展实现；isFTDI参数未实际使用。

        Args:
            RTS (int, optional): RTS线状态（1=置高），默认None
            DTR (int, optional): DTR线状态（1=置高），默认None
            isFTDI (bool, optional): 是否为FTDI芯片串口（未使用），默认False
            
        """
        try:
            if RTS == 1:
                self.device.rts = RTS
                self.debug(f"Set RTS line to {RTS}")
            if DTR == 1:
                self.device.dtr = DTR
                self.debug(f"Set DTR line to {DTR}")
            self.debug("Serial control line state updated")
        except Exception as err:
            self.error(f"Failed to set control line state: {str(err)}")

    def write(self, command: str | bytes, data_pack_size: int = 512):
        """ 向串口写入数据.

        支持字符串/字节类型数据，默认按512字节分片发送；空字节写入做超时重试，
        非空数据发送失败时重试3次；发送完成后刷新输出缓冲区并短延时等待响应。

        Args:
            command (str/bytes): 待发送的数据（字符串自动转UTF-8字节）
            data_pack_size (int, optional): 分片发送的数据包大小，默认512字节

        Returns:
            bool: 发送成功返回True，失败返回False
            
        """
        if isinstance(command, str):
            command = command.encode('utf-8')
            
        pos = 0
        if command == b'':
            try:
                self.device.write(b'')
            except Exception as err:
                error = str(err)
                if 'time_out' in error:
                    # time.sleep(0.01)
                    try:
                        self.device.write(b'')
                    except Exception as err:
                        self.debug(str(err))
                        return False
                return True
            
        else:
            retry_count = 0
            while pos < len(command):
                try:
                    sent_bytes = self.device.write(command[pos:pos + data_pack_size])
                    if sent_bytes <= 0:
                        self.info(f"Sent {sent_bytes} bytes (expected {data_pack_size})")
                    pos += sent_bytes
                except Exception as err:
                    self.debug(f"Write error (pos: {pos}): {str(err)}")
                    # print("Error while writing")
                    # time.sleep(0.01)
                    retry_count += 1
                    if retry_count == 3:
                        self.error(f"Write failed after 3 retries: {str(err)}")
                        return False
                    time.sleep(0.01)  # 重试前短延时
                    
        self.verify_data(bytearray(command), "TX:")
        # self.device.flushOutput()
        self.device.flush()
        time.sleep(0.005)
        
        return True

    def read(self, length: int | None = None, time_out: int = -1) -> bytes:
        """ 封装串口读操作，适配XML解析模式.

        若未指定长度，读取缓冲区所有数据；超时使用实例默认值（time_out=-1时）；
        XML模式下限制读取长度不超过缓冲区现有数据量。

        Args:
            length (int, optional): 读取字节数，默认读取缓冲区所有数据
            time_out (int, optional): 超时时间（秒），默认-1（使用实例timeout属性）

        Returns:
            bytes: 读取到的字节数据，超时/失败返回空字节
            
        """
        if time_out == -1:
            time_out = self.timeout
        if length is None:
            length = self.device.in_waiting
            if length == 0:
                return b""
            
        if self.xml_read:
            if length > self.device.in_waiting:
                length = self.device.in_waiting
                
        return self.usb_read(length, time_out)

    def flush(self):
        """ 刷新串口输入/输出缓冲区.

        调用pyserial的flush()方法，清空未发送/未读取的数据。
        
        """
        return self.device.flush()

    def usb_read(self, resp_len: int | None = None, time_out: int = 0) -> bytes:
        """ 串口核心读操作，支持XML格式数据特殊解析.

        XML模式下匹配"<?xml "开头和"</data>"结尾的完整XML数据；
        普通模式下读取指定长度数据，处理超时、USB溢出等异常。

        Args:
            resp_len (int, optional): 期望读取的字节数，默认读取缓冲区所有数据
            time_out (int, optional): 超时时间（秒），默认0

        Returns:
            bytes: 读取到的字节数据，异常/超时返回空字节
            
        """
        if resp_len is None:
            resp_len = self.device.in_waiting
        if resp_len <= 0:
            self.info("Warning !")
            
        res = bytearray()
        log_level = self.loglevel
        self.device.timeout = time_out
        device_read = self.device.read
        extend = res.extend
        
        if self.xml_read:
            xml_header = self.device.read(6)
            extend(xml_header)
            if b'<?xml ' in xml_header:
                while b'response ' not in res or res[-7:] != b'</data>':
                    extend(device_read(1))
                return res
            
        bytes_to_read = resp_len
        while len(res) < bytes_to_read:
            try:
                read_data = device_read(bytes_to_read)
                if len(read_data) == 0:
                    break
                extend(read_data)
                bytes_to_read -= len(read_data)
                
            except Exception as err:
                error = str(err)
                if 'timed out' in error:
                    if time_out is None:
                        return b''
                    self.debug(f'Read timeout (current timeout: {time_out}s)')
                    if time_out == 10:
                        return b''
                    time_out += 1
                    
                elif 'Overflow' in error:
                    self.error('USB Overflow error during read')
                    return b''
                
                else:
                    self.info(f'Unknown read error: {repr(err)}')
                    return b''

        if log_level == logging.DEBUG:
            self.debug(inspect.currentframe().f_back.f_code.co_name + ":" + hex(resp_len))
            self.verify_data(res[:resp_len], "RX:")
        return res[:resp_len]

    def usb_write(self, data: str | bytes, data_pack_size: int | None = None) -> bool:
        """ 封装写操作+缓冲区刷新.

        调用write()方法发送数据，发送完成后立即刷新输出缓冲区。

        Args:
            data (str/bytes): 待发送的数据
            data_pack_size (int, optional): 分片发送的数据包大小，默认None

        Returns:
            bool: 发送成功返回True，失败返回False
            
        """
        if data_pack_size is None:
            data_pack_size = len(data)
        result = self.write(data, data_pack_size)
        self.device.flush()
        return result

    def usb_read_write(self, data: str | bytes, resp_len: int) -> bytes:
        """ 串口写读一体操作（先写后读）.

        发送指定数据后，立即读取指定长度的响应数据，适用于请求-响应式通信场景。

        Args:
            data (str/bytes): 待发送的请求数据
            resp_len (int): 期望读取的响应字节数

        Returns:
            bytes: 读取到的响应数据，失败返回空字节
            
        """
        self.usb_write(data)  # size
        self.device.flush()
        res = self.usb_read(resp_len)
        return res
    
    def get_interface_count(self) -> int:
        """获取串口设备的可用接口数量（串口默认1个通信接口）。

        Returns:
            int: 接口数量，默认返回1
        """
        return 1  # 串口设备默认单接口，直接返回1
    
    def ctrl_transfer(self, request_type: int, request: int, value: int,
                      index: int, data_or_length: bytes | int) -> bytes | int:
        """执行USB控制传输（串口设备适配实现）。

        串口设备默认不支持USB控制传输，若为USB转串口芯片（如FTDI），需扩展对应逻辑。

        Args:
            request_type (int): USB请求类型（方向、类型、接收者）
            request (int): USB请求码
            value (int): 请求数值参数
            index (int): 请求索引参数
            data_or_length (bytes | int): 发送数据（OUT请求）或接收长度（IN请求）

        Returns:
            bytes | int: 输入传输返回空字节，输出传输返回0
        """
        self.warning('Serial device does not support USB control transfer by default.')
        if isinstance(data_or_length, int):
            # 输入传输（主机读设备）：返回空字节
            return b''
        else:
            # 输出传输（主机写设备）：返回0表示未发送
            return 0
