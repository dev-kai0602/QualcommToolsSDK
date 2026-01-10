#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!
import array
import inspect
import logging
from binascii import hexlify
from ctypes import c_void_p, c_int
from enum import Enum
from struct import pack

import usb.backend.libusb0
import usb.core  # pyusb
import usb.util

from edlclient.Library.utils import *
from edlclient.Library.Connection.device_handler import DeviceClass

if not is_windows():
    import usb.backend.libusb1

# -------------------------- 全局常量定义 --------------------------
""" USB 传输方向常量 """
USB_DIR_OUT = 0  # 数据输出到设备（主机->设备）
USB_DIR_IN = 0x80  # 数据输入到主机（设备->主机）

""" USB 请求类型掩码（bRequestType 字段第二位） """
USB_TYPE_MASK = (0x03 << 5)
USB_TYPE_STANDARD = (0x00 << 5)  # 标准请求
USB_TYPE_CLASS = (0x01 << 5)     # 类请求（如 CDC 类）
USB_TYPE_VENDOR = (0x02 << 5)    # 厂商自定义请求
USB_TYPE_RESERVED = (0x03 << 5)  # 保留类型

""" USB 接收者掩码（bRequestType 字段第三位） """
USB_RECIP_MASK = 0x1f
USB_RECIP_DEVICE = 0x00      # 接收者：设备
USB_RECIP_INTERFACE = 0x01   # 接收者：接口
USB_RECIP_ENDPOINT = 0x02    # 接收者：端点
USB_RECIP_OTHER = 0x03       # 接收者：其他
USB_RECIP_PORT = 0x04        # 接收者：端口（无线 USB 1.0）
USB_RECIP_RPIPE = 0x05       # 接收者：管道（无线 USB 1.0）

""" USB 批量传输最大缓冲区大小 """
MAX_USB_BULK_BUFFER_SIZE = 16384

""" SCSI 命令全局标签（用于标识命令块） """
tag = 0

""" CDC 类核心命令集（通信设备类标准命令） """
CDC_CMDS = {
    "SEND_ENCAPSULATED_COMMAND": 0x00,    # 发送封装命令
    "GET_ENCAPSULATED_RESPONSE": 0x01,    # 获取封装响应
    "SET_COMM_FEATURE": 0x02,             # 设置通信特性
    "GET_COMM_FEATURE": 0x03,             # 获取通信特性
    "CLEAR_COMM_FEATURE": 0x04,           # 清除通信特性
    "SET_LINE_CODING": 0x20,              # 设置串口线编码（波特率/数据位等）
    "GET_LINE_CODING": 0x21,              # 获取串口线编码
    "SET_CONTROL_LINE_STATE": 0x22,       # 设置控制线路状态（RTS/DTR）
    "SEND_BREAK": 0x23,                   # 发送中断信号（参数为中断时长）
}


class USBClass(DeviceClass):
    """
    USB 设备通信核心类
    封装 USB 设备连接、数据读写、控制传输、CDC 配置等核心功能，
    继承自 DeviceClass（基础设备处理类），支持跨平台兼容。

    Attributes:
        serial_number (str): 设备序列号（用于精准匹配设备）
        EP_IN (usb.core.Endpoint): 输入端点（设备->主机）
        EP_OUT (usb.core.Endpoint): 输出端点（主机->设备）
        is_serial (bool): 是否为串口设备
        buffer (array.array): 数据接收缓冲区
        backend (usb.backend): libusb 后端实例（跨平台适配）
        device (usb.core.Device): 已连接的 USB 设备实例
        configuration (usb.core.Configuration): 设备激活的配置
        interface (int/usb.core.Interface): 设备接口号/接口实例
        maxsize (int): 输入端点最大数据包长度
        connected (bool): 设备是否已连接
        
    """

    def __init__(self, log_level: int = logging.INFO, port_config: list | None = None, dev_class: int = -1,
                 serial_number: str | None = None, enabled_log: bool = False, enabled_print: bool = False):
        """ 初始化 USB 通信类

        Args:
            log_level (int): 日志级别（默认 logging.INFO）
            port_config (list): 端口配置列表，格式 [(VID, PID, 接口号), ...]
            dev_class (int): 设备类筛选（-1 表示不筛选）
            serial_number (str): 设备序列号（精准匹配设备）
            enabled_log – 是否启用日志记录功能，默认关闭
            enabled_print – 是否启用控制台打印功能，默认关闭
            
        """
        super().__init__(log_level, port_config, dev_class, enabled_log, enabled_print)
        self.serial_number = serial_number
        self.load_windows_dll() # Windows 平台加载 libusb DLL
        self.EP_IN = None
        self.EP_OUT = None
        self.is_serial = False
        self.buffer = array.array('B', [0]) * 1048576 # 初始化 1MB 缓冲区
        
        # 跨平台 libusb 后端适配
        if sys.platform.startswith('freebsd') or sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
            # Linux/macOS/FreeBSD 使用 libusb1 后端
            self.backend = usb.backend.libusb1.get_backend(find_library=lambda x: "libusb-1.0.so")
        elif is_windows():
            # Windows 自动适配后端（依赖 DLL）
            self.backend = None
            
        # 尝试设置 libusb 选项（优化通信）
        if self.backend is not None:
            try:
                self.backend.lib.libusb_set_option.argtypes = [c_void_p, c_int]
                self.backend.lib.libusb_set_option(self.backend.ctx, 1)
            except:
                self.backend = None

    def load_windows_dll(self):
        """
        Windows 平台加载 libusb 动态库
        自动添加 DLL 搜索路径，解决 Windows 下 libusb 依赖问题
        
        """
        if os.name == 'nt':
            windows_dir = None
            try:
                # add pygame folder to Windows DLL search paths
                # 拼接 Windows 平台 DLL 目录路径
                windows_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../..", "Windows")
                try:
                    os.add_dll_directory(windows_dir)
                except Exception:
                    pass
                # 更新系统 PATH 环境变量
                os.environ['PATH'] = windows_dir + ';' + os.environ['PATH']
            except Exception as err:
                self.debug(f"加载 Windows DLL 失败: {err}")
            finally:
                del windows_dir  # 释放临时变量

    def get_interface_count(self) -> int | bool:
        """ 获取 USB 设备的接口数量

        Returns:
            int/false: 成功返回接口数量，失败返回 False
            
        """
        if self.vid is not None:
            # 根据 VID/PID 查找设备
            self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid, backend=self.backend)
            if self.device is None:
                self.debug("Couldn't detect the device. Is it connected ?")
                return False
            
            # 尝试设置设备配置
            try:
                self.device.set_configuration()
            except Exception as err:
                self.debug(f"设置设备配置失败: {err}")
            
            # 获取激活的配置并返回接口数量
            self.configuration = self.device.get_active_configuration()
            self.debug(2, self.configuration)
            return self.configuration.bNumInterfaces
        
        else:
            self._logger.error("No device detected. Is it connected ?")
            
        return 0

    def set_line_coding(self, baud_rate: int | None = None, parity: int = 0, data_bits: int = 8, stop_bits: float = 1):
        """
        设置 CDC 串口线编码（波特率、数据位、停止位、奇偶校验）
        严格校验参数合法性，仅支持标准串口参数

        Args:
            baud_rate (int): 波特率（仅支持 300/9600/115200 等标准值）
            parity (int): 奇偶校验（0=无校验,1=奇校验,2=偶校验,3=标记,4=空格）
            data_bits (int): 数据位（5/6/7/8/16）
            stop_bits (float): 停止位（1/1.5/2）

        Raises:
            ValueError: 参数不在合法范围内时抛出
            
        """
        # 合法参数映射表
        sbits = {1: 0, 1.5: 1, 2: 2}       # 停止位映射（协议值）
        dbits = {5, 6, 7, 8, 16}            # 合法数据位
        pmodes = {0, 1, 2, 3, 4}            # 合法奇偶校验模式
        brates = {300, 600, 1200, 2400, 4800, 9600, 14400,
                  19200, 28800, 38400, 57600, 115200, 230400}  # 合法波特率
        
        # 校验停止位
        if stop_bits is not None:
            if stop_bits not in sbits.keys():
                valid = ", ".join(str(k) for k in sorted(sbits.keys()))
                raise ValueError("Valid stop_bits are " + valid)
            self.stop_bits = stop_bits
        else:
            self.stop_bits = 0
        
        # 校验数据位
        if data_bits is not None:
            if data_bits not in dbits:
                valid = ", ".join(str(d) for d in sorted(dbits))
                raise ValueError("Valid data_bits are " + valid)
            self.data_bits = data_bits
        else:
            self.data_bits = 0
        
        # 校验奇偶校验
        if parity is not None:
            if parity not in pmodes:
                valid = ", ".join(str(pm) for pm in sorted(pmodes))
                raise ValueError("Valid parity modes are " + valid)
            self.parity = parity
        else:
            self.parity = 0
        
        # 校验波特率（自动推荐最近合法值）
        if baud_rate is not None:
            if baud_rate not in brates:
                brs = sorted(brates)
                dif = [abs(br - baud_rate) for br in brs]
                best = brs[dif.index(min(dif))]
                raise ValueError("Invalid baudrates, nearest valid is {}".format(best))
            self.baud_rate = baud_rate
        
        # 构造线编码数据（按 CDC 协议格式）
        linecode = [
            self.baud_rate & 0xff,
            (self.baud_rate >> 8) & 0xff,
            (self.baud_rate >> 16) & 0xff,
            (self.baud_rate >> 24) & 0xff,
            sbits[self.stop_bits],
            self.parity,
            self.data_bits]

        # 构造控制传输请求类型
        txdir = 0  # 输出方向（主机->设备）
        req_type = 1  # 类请求
        recipient = 1  # 接收者：接口
        req_type = (txdir << 7) + (req_type << 5) + recipient
        
        # 发送控制传输设置线编码
        data = bytearray(linecode)
        wlen = self.device.ctrl_transfer(
            req_type, CDC_CMDS["SET_LINE_CODING"],
            data_or_wLength=data, index=1)
        self.debug("Linecoding set, {}b sent".format(wlen))

    def set_break(self):
        """
        发送 CDC 中断信号（SEND_BREAK 命令）
        用于串口中断控制，如触发设备重置/唤醒
        
        """
        # 构造控制传输请求类型
        txdir = 0  # 输出方向
        req_type = 1  # 类请求
        recipient = 1  # 接收者：接口
        req_type = (txdir << 7) + (req_type << 5) + recipient
        
        # 发送控制传输
        wlen = self.device.ctrl_transfer(
            request_type=req_type, request=CDC_CMDS["SEND_BREAK"],
            value=0, data_or_wLength=0, index=1)
        self.debug("Break set, {}b sent".format(wlen))

    def set_control_line_state(self, RTS: bool = None, DTR: bool = None, isFTDI: bool = False):
        """
        设置 CDC 控制线路状态（RTS/DTR 信号）
        适配 FTDI 芯片与标准 CDC 设备的差异

        Args:
            RTS (bool): RTS 信号状态（True=启用，False=禁用）
            DTR (bool): DTR 信号状态（True=启用，False=禁用）
            isFTDI (bool): 是否为 FTDI 芯片设备（特殊处理）
            
        """
        # 计算控制状态值（标准 CDC）
        ctrl_state = (2 if RTS else 0) + (1 if DTR else 0)
        
        # FTDI 芯片特殊处理
        if isFTDI:
            ctrl_state += (1 << 8) if DTR is not None else 0
            ctrl_state += (2 << 8) if RTS is not None else 0
            
        # 构造请求类型（区分 FTDI 与标准 CDC）
        txdir = 0  # 输出方向
        req_type = 2 if isFTDI else 1  # FTDI 使用厂商请求，标准 CDC 使用类请求
        recipient = 0 if isFTDI else 1  # FTDI 接收者为设备，标准 CDC 为接口
        req_type = (txdir << 7) + (req_type << 5) + recipient
        
        # 发送控制传输
        wlen = self.device.ctrl_transfer(
            request_type=req_type,
            request=1 if isFTDI else CDC_CMDS["SET_CONTROL_LINE_STATE"],
            value=ctrl_state,
            index=1,
            data_or_wLength=0)
        self.debug("Linecoding set, {}b sent".format(wlen))

    def flush(self):
        """
        刷新缓冲区（占位方法，暂无实现）
        用于兼容串口设备的缓冲区刷新逻辑
        """
        pass

    def connect(self, EP_IN: int = -1, EP_OUT: int = -1, port_name: str = ""):
        """
        连接 USB 设备
        1. 枚举系统 USB 设备，匹配 VID/PID/序列号
        2. 查找 IN/OUT 端点（自动/指定）
        3. 分离内核驱动，占用设备接口
        4. 标记设备为已连接状态

        Args:
            EP_IN (int): 指定输入端点号（-1 表示自动查找）
            EP_OUT (int): 指定输出端点号（-1 表示自动查找）
            port_name (str): 端口名（占位参数，暂无使用）

        Returns:
            bool: 连接成功返回 True，失败返回 False
            
        """
        # 若已连接，先关闭旧连接
        if self.connected:
            self.close()
            self.connected = False
        
        # 重置设备/端点状态
        self.device = None
        self.EP_OUT = None
        self.EP_IN = None
        
        # 枚举系统所有 USB 设备
        devices = usb.core.find(find_all=True, backend=self.backend)
        for dev in devices:
            # 匹配端口配置中的 VID/PID
            for usbid in self.port_config:
                if dev.idProduct == usbid[1] and dev.idVendor == usbid[0]:
                    # 匹配序列号（若指定）
                    if self.serial_number is not None:
                        if dev.serial_number != self.serial_number:
                            continue
                    # 匹配成功，记录设备信息
                    self.device = dev
                    self.vid = dev.idVendor
                    self.pid = dev.idProduct
                    self.serial_number = dev.serial_number
                    self.interface = usbid[2]
                    break
            if self.device is not None:
                break
        
        # 设备未找到
        if self.device is None:
            self.debug("Couldn't detect the device. Is it connected ?")
            return False
        
        # 获取设备配置（处理未设置配置的情况）
        try:
            self.configuration = self.device.get_active_configuration()
            
        except usb.core.USBError as err:
            if str(err) == 'Configuration not set':
                self.device.set_configuration()
                self.configuration = self.device.get_active_configuration()
            # Linux 权限问题处理
            if err.errno == 13:
                self.error("Permission denied accessing {:04x}:{:04x}.".format(self.vid,self.pid))
                self.info("Potential fix (update udev rules): sudo echo 'SUBSYSTEM==\"usb\",ATTRS{{idVendor}}==\"{:04x}\",ATTRS{{idProduct}}==\"{:04x}\",MODE=\"0666\"' >> /etc/udev/rules.d/99-edl.rules".format(self.vid,self.pid))
                # 切换到 libusb0 后端重试
                self.backend = usb.backend.libusb0.get_backend()
                self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid, backend=self.backend)
        
        # 配置获取失败
        if self.configuration is None:
            self.error("Couldn't get device configuration.")
            return False
        
        # 校验接口号合法性
        if self.interface > self.configuration.bNumInterfaces:
            print("Invalid interface, max number is %d" % self.configuration.bNumInterfaces)
            return False
        
        # 查找匹配的接口和端点
        for itf in self.configuration:
            # 筛选设备类（-1 表示不筛选）
            if self.dev_class == -1:
                self.dev_class = 0xFF
            if itf.bInterfaceClass == self.dev_class:
                if self.interface == -1 or self.interface == itf.bInterfaceNumber:
                    self.interface = itf
                    self.EP_OUT = EP_OUT
                    self.EP_IN = EP_IN
                    # 遍历端点，匹配 IN/OUT 方向
                    for ep in itf:
                        edir = usb.util.endpoint_direction(ep.bEndpointAddress)
                        # 匹配输出端点
                        if (edir == usb.util.ENDPOINT_OUT and EP_OUT == -1) or ep.bEndpointAddress == (EP_OUT & 0xF):
                            self.EP_OUT = ep
                        # 匹配输入端点
                        elif (edir == usb.util.ENDPOINT_IN and EP_IN == -1) or ep.bEndpointAddress == (EP_OUT & 0xF):
                            self.EP_IN = ep
                    break
        
        # 端点匹配成功，初始化设备
        if self.EP_OUT is not None and self.EP_IN is not None:
            self.maxsize = self.EP_IN.wMaxPacketSize
            # 分离内核驱动（若已加载）
            try:
                if self.device.is_kernel_driver_active(0):
                    self.debug("Detaching kernel driver")
                    self.device.detach_kernel_driver(0)
            except Exception as err:
                self.debug("No kernel driver supported: " + str(err))
            
            # 占用设备接口
            try:
                usb.util.claim_interface(self.device, 0)
            except Exception:
                pass
            
            # 标记为已连接
            self.connected = True
            return True
        
        # 未找到 CDC 接口
        self._print("Couldn't find CDC interface. Aborting.")
        self.connected = False
        return False

    def close(self, reset: bool = False):
        """
        关闭 USB 设备连接
        1. 释放设备资源
        2. 可选重置设备
        3. 恢复内核驱动（避免设备占用）

        Args:
            reset (bool): 是否重置设备（默认 False）
            
        """
        if self.connected:
            try:
                # 重置设备（若指定）
                if reset:
                    self.device.reset()
                # 恢复内核驱动（仅当未激活时）
                if not self.device.is_kernel_driver_active(self.interface):
                    self.device.attach_kernel_driver(0)
                    
            except Exception as err:
                self.debug(str(err))
            
            # 释放 USB 资源
            usb.util.dispose_resources(self.device)
            del self.device
            
            # 重置后延迟（避免设备未就绪）
            if reset:
                time.sleep(2)
            self.connected = False

    def write(self, command: str | bytes, data_pack_size: int = None) -> bool:
        """
        批量写数据到 USB 设备
        1. 支持字符串/字节数据自动转换
        2. 分块发送（默认 16384 字节）
        3. 异常重试（最多 3 次）

        Args:
            command (str/bytes): 要发送的数据
            data_pack_size (int): 分块大小（默认 MAX_USB_BULK_BUFFER_SIZE）

        Returns:
            bool: 发送成功返回 True，失败返回 False
            
        """
        # 默认分块大小
        if data_pack_size is None:
            # data_pack_size = self.EP_OUT.wMaxPacketSize
            data_pack_size = MAX_USB_BULK_BUFFER_SIZE
        
        # 字符串转字节
        if isinstance(command, str):
            command = bytes(command, 'utf-8')
            
        pos = 0
        # 空数据处理
        if command == b'':
            try:
                self.EP_OUT.write(b'')
            except usb.core.USBError as err:
                error = str(err.strerror)
                if "time_out" in error:
                    # 超时重试
                    # time.sleep(0.01)
                    try:
                        self.EP_OUT.write(b'')
                    except Exception as err:
                        self.debug(str(err))
                        return False
                return True
            
        else:
            # 分块发送数据
            retry = 0
            while pos < len(command):
                try:
                    # 发送当前块数据
                    ctr = self.EP_OUT.write(command[pos:pos + data_pack_size])
                    if ctr <= 0:
                        self.info(ctr)
                    pos += data_pack_size
                    retry = 0  # 重置重试计数
                    
                except Exception as err:
                    self.debug(str(err))
                    # print("Error while writing")
                    # time.sleep(0.01)
                    retry += 1
                    if retry == 3:
                        return False
        
        # 校验发送数据（调试模式）
        self.verify_data(bytearray(command), "TX:")
        return True

    def usb_read(self, resp_len: int = None, time_out: int = 1) -> bytes:
        """
        从 USB 设备批量读数据
        1. 按最大包长拼接数据
        2. 处理超时/溢出等异常
        3. 调试模式下打印数据

        Args:
            resp_len (int): 期望读取长度（默认端点最大包长）
            time_out (int): 超时时间（秒，0 表示默认 1 秒）

        Returns:
            bytes: 读取到的数据（失败返回空字节）
            
        """
        # 默认读取长度为端点最大包长
        if resp_len is None:
            resp_len = self.maxsize
        # 校验读取长度
        if resp_len <= 0:
            self.info("Warning !")
            
        res = bytearray()
        loglevel = self.loglevel
        buffer = self.buffer[:resp_len]
        epr = self.EP_IN.read
        extend = res.extend
        
        # 循环读取直到满足长度
        while len(res) < resp_len:
            try:
                resp_len = epr(buffer, time_out)
                extend(buffer[:resp_len])
                if resp_len == self.EP_IN.wMaxPacketSize:
                    break
            except usb.core.USBError as e:
                error = str(e.strerror)
                if "timed out" in error:
                    if time_out is None:
                        return b""
                    self.debug("Timed out")
                    if time_out == 10:
                        return b""
                    time_out += 1
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

    def ctrl_transfer(self, request_type, request, value, index, data_or_wLength):
        ret = self.device.ctrl_transfer(request_type=request_type, request=request, value=value, index=index,
                                        data_or_wLength=data_or_wLength)
        return ret[0] | (ret[1] << 8)

    class deviceclass:
        vid = 0
        pid = 0

        def __init__(self, vid, pid):
            self.vid = vid
            self.pid = pid

    def detect_devices(self):
        dev = usb.core.find(find_all=True, backend=self.backend)
        ids = [self.deviceclass(cfg.idVendor, cfg.idProduct) for cfg in dev]
        return ids

    def usb_write(self, data, data_pack_size=None):
        if data_pack_size is None:
            data_pack_size = len(data)
        res = self.write(data, data_pack_size)
        # port->flush()
        return res

    def usb_read_write(self, data, resp_len):
        self.usb_write(data)  # size
        # port->flush()
        res = self.usb_read(resp_len)
        return res


class ScsiCmds(Enum):
    SC_TEST_UNIT_READY = 0x00,
    SC_REQUEST_SENSE = 0x03,
    SC_FORMAT_UNIT = 0x04,
    SC_READ_6 = 0x08,
    SC_WRITE_6 = 0x0a,
    SC_INQUIRY = 0x12,
    SC_MODE_SELECT_6 = 0x15,
    SC_RESERVE = 0x16,
    SC_RELEASE = 0x17,
    SC_MODE_SENSE_6 = 0x1a,
    SC_START_STOP_UNIT = 0x1b,
    SC_SEND_DIAGNOSTIC = 0x1d,
    SC_PREVENT_ALLOW_MEDIUM_REMOVAL = 0x1e,
    SC_READ_FORMAT_CAPACITIES = 0x23,
    SC_READ_CAPACITY = 0x25,
    SC_WRITE_10 = 0x2a,
    SC_VERIFY = 0x2f,
    SC_READ_10 = 0x28,
    SC_SYNCHRONIZE_CACHE = 0x35,
    SC_READ_TOC = 0x43,
    SC_READ_HEADER = 0x44,
    SC_MODE_SELECT_10 = 0x55,
    SC_MODE_SENSE_10 = 0x5a,
    SC_READ_12 = 0xa8,
    SC_WRITE_12 = 0xaa,
    SC_PASCAL_MODE = 0xff


command_block_wrapper = [
    ('dCBWSignature', '4s'),
    ('dCBWTag', 'I'),
    ('dCBWDataTransferLength', 'I'),
    ('bmCBWFlags', 'B'),
    ('bCBWLUN', 'B'),
    ('bCBWCBLength', 'B'),
    ('CBWCB', '16s'),
]
command_block_wrapper_len = 31

command_status_wrapper = [
    ('dCSWSignature', '4s'),
    ('dCSWTag', 'I'),
    ('dCSWDataResidue', 'I'),
    ('bCSWStatus', 'B')
]
command_status_wrapper_len = 13


class Scsi:
    """
    FIHTDC, PCtool
    """
    SC_READ_NV = 0xf0
    SC_SWITCH_STATUS = 0xf1
    SC_SWITCH_PORT = 0xf2
    SC_MODEM_STATUS = 0xf4
    SC_SHOW_PORT = 0xf5
    SC_MODEM_DISCONNECT = 0xf6
    SC_MODEM_CONNECT = 0xf7
    SC_DIAG_RUT = 0xf8
    SC_READ_BATTERY = 0xf9
    SC_READ_IMAGE = 0xfa
    SC_ENABLE_ALL_PORT = 0xfd
    SC_MASS_STORGE = 0xfe
    SC_ENTER_DOWNLOADMODE = 0xff
    SC_ENTER_FTMMODE = 0xe0
    SC_SWITCH_ROOT = 0xe1
    """
    //Div2-5-3-Peripheral-LL-ADB_ROOT-00+/* } FIHTDC, PCtool */
    //StevenCPHuang 2011/08/12 porting base on 1050 --
    //StevenCPHuang_20110820,add Moto's mode switch cmd to support PID switch function ++
    """
    SC_MODE_SWITCH = 0xD6

    # /StevenCPHuang_20110820,add Moto's mode switch cmd to support PID switch function --

    def __init__(self, loglevel=logging.INFO, vid=None, pid=None, interface=-1):
        self.vid = vid
        self.pid = pid
        self.interface = interface
        self.Debug = False
        self.usb = None
        self.loglevel = loglevel

    def connect(self):
        self.usb = USBClass(log_level=self.loglevel, port_config=[self.vid, self.pid, self.interface], dev_class=8)
        if self.usb.connect():
            return True
        return False

    # htcadb = "55534243123456780002000080000616687463800100000000000000000000";
    # Len 0x6, Command 0x16, "HTC" 01 = Enable, 02 = Disable
    def send_mass_storage_command(self, lun, cdb, direction, data_length):
        global tag
        cmd = cdb[0]
        if 0 <= cmd < 0x20:
            cdb_len = 6
        elif 0x20 <= cmd < 0x60:
            cdb_len = 10
        elif 0x60 <= cmd < 0x80:
            cdb_len = 0
        elif 0x80 <= cmd < 0xA0:
            cdb_len = 16
        elif 0xA0 <= cmd < 0xC0:
            cdb_len = 12
        else:
            cdb_len = 6

        if len(cdb) != cdb_len:
            print("Error, cdb length doesn't fit allowed cbw packet length")
            return 0

        if (cdb_len == 0) or (cdb_len > command_block_wrapper_len):
            print("Error, invalid data packet length, should be max of 31 bytes.")
            return 0
        else:
            data = write_object(command_block_wrapper, b"USBC", tag, data_length, direction, lun, cdb_len, cdb)[
                'raw_data']
            if len(data) != 31:
                print("Error, invalid data packet length, should be 31 bytes, but length is %d" % len(data))
                return 0
            tag += 1
            self.usb.write(data, 31)
        return tag

    def send_htc_adbenable(self):
        # do_reserve from f_mass_storage.c
        print("Sending HTC adb enable command")
        common_cmnd = b"\x16htc\x80\x01"  # reserve_cmd + 'htc' + len + flag
        '''
        Flag values:
            1: Enable adb daemon from mass_storage
            2: Disable adb daemon from mass_storage
            3: cancel unmount BAP cdrom
            4: cancel unmount HSM rom
        '''
        lun = 0
        datasize = common_cmnd[4]
        timeout = 5000
        ret_tag = self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, datasize)
        ret_tag += self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, datasize)
        if datasize > 0:
            data = self.usb.read(datasize, timeout)
            print("DATA: " + hexlify(data).decode('utf-8'))
        print("Sent HTC adb enable command")

    def send_htc_ums_adbenable(self):  # HTC10
        # ums_ctrlrequest from f_mass_storage.c
        print("Sending HTC ums adb enable command")
        brequesttype = USB_DIR_IN | USB_TYPE_VENDOR | USB_RECIP_DEVICE
        brequest = 0xa0
        wvalue = 1
        '''
        value:
            0: Disable adb daemon
            1: Enable adb daemon
        '''
        windex = 0
        w_length = 1
        ret = self.usb.ctrl_transfer(brequesttype, brequest, wvalue, windex, w_length)
        print("Sent HTC ums adb enable command: %x" % ret)

    def send_zte_adbenable(self):  # zte blade
        common_cmnd = b"\x86zte\x80\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # reserve_cmd + 'zte' + len + flag
        common_cmnd2 = b"\x86zte\x80\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # reserve_cmd + 'zte' + len + flag
        '''
        Flag values:
            0: disable adbd ---for 736T
            1: enable adbd ---for 736T
            2: disable adbd ---for All except 736T
            3: enable adbd ---for All except 736T
        '''
        lun = 0
        datasize = common_cmnd[4]
        timeout = 5000
        ret_tag = self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, datasize)
        ret_tag += self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, datasize)
        ret_tag = self.send_mass_storage_command(lun, common_cmnd2, USB_DIR_IN, datasize)
        ret_tag += self.send_mass_storage_command(lun, common_cmnd2, USB_DIR_IN, datasize)
        if datasize > 0:
            data = self.usb.read(datasize, timeout)
            print("DATA: " + hexlify(data).decode('utf-8'))
        print("Send HTC adb enable command")

    def send_fih_adbenable(self):  # motorola xt560, nokia 3.1, #f_mass_storage.c
        if self.usb.connect():
            print("Sending FIH adb enable command")
            datasize = 0x24
            # reserve_cmd + 'FI' + flag + len + none
            common_cmnd = bytes([self.SC_SWITCH_PORT]) + b"FI1" + pack("<H", datasize)
            '''
            Flag values:
                common_cmnd[3]->1: Enable adb daemon from mass_storage
                common_cmnd[3]->0: Disable adb daemon from mass_storage
            '''
            lun = 0
            # datasize=common_cmnd[4]
            timeout = 5000
            ret_tag = None
            ret_tag += self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, 0x600)
            # ret_tag+=self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, 0x600)
            if datasize > 0:
                data = self.usb.read(datasize, timeout)
                print("DATA: " + hexlify(data).decode('utf-8'))
            print("Sent FIH adb enable command")
            self.usb.close()

    def send_alcatel_adbenable(self):  # Alcatel MW41
        if self.usb.connect():
            print("Sending alcatel adb enable command")
            datasize = 0x24
            common_cmnd = b"\x16\xf9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            lun = 0
            timeout = 5000
            ret_tag = None
            ret_tag += self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, 0x600)
            if datasize > 0:
                data = self.usb.read(datasize, timeout)
                print("DATA: " + hexlify(data).decode('utf-8'))
            print("Sent alcatel adb enable command")
            self.usb.close()

    def send_fih_root(self):
        # motorola xt560, nokia 3.1, huawei u8850, huawei Ideos X6,
        # lenovo s2109, triumph M410, viewpad 7, #f_mass_storage.c
        if self.usb.connect():
            print("Sending FIH root command")
            datasize = 0x24
            # reserve_cmd + 'FIH' + len + flag + none
            common_cmnd = bytes([self.SC_SWITCH_ROOT]) + b"FIH" + pack("<H", datasize)
            lun = 0
            # datasize = common_cmnd[4]
            timeout = 5000
            ret_tag = self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, 0x600)
            ret_tag += self.send_mass_storage_command(lun, common_cmnd, USB_DIR_IN, 0x600)
            if datasize > 0:
                data = self.usb.read(datasize, timeout)
                print("DATA: " + hexlify(data).decode('utf-8'))
            print("Sent FIH root command")
            self.usb.close()

    def close(self):
        self.usb.close()
        return True
