#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2025 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!

"""
Usage:
    edl -h | --help
    edl [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]
    edl [--loader=filename] [--memory=memtype] [--port_name=port_name] [--serial]
    edl [--debugmode] [--port_name=port_name] [--serial]
    edl [--gpt-num-part-entries=number] [--gpt-part-entry-size=number] [--gpt-part-entry-start-lba=number] [--port_name=port_name] [--serial]
    edl [--memory=memtype] [--skipstorageinit] [--maxpayload=bytes] [--sectorsize==bytes] [--port_name=port_name] [--serial]
    edl server [--tcpport=portnumber] [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl memorydump [--partitions=partnames] [--debugmode] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial] [--serial_number=serial_number]
    edl printgpt [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--loader=filename] [--debugmode]  [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl gpt <directory> [--memory=memtype] [--lun=lun] [--genxml] [--loader=filename]  [--skipresponse] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl r <partitionname> <filename> [--memory=memtype] [--sectorsize==bytes] [--lun=lun] [--loader=filename]  [--skipresponse] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl rl <directory> [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--skip=partnames] [--genxml]  [--skipresponse] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl rf <filename> [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--loader=filename] [--debugmode]  [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl rs <start_sector> <sectors> <filename> [--lun=lun] [--sectorsize==bytes] [--memory=memtype] [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl w <partitionname> <filename> [--partitionfilename=filename] [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--skipwrite] [--skipresponse] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--devicemodel=value] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl wl <directory> [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--skip=partnames] [--skipresponse] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--devicemodel=value] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl wf <filename> [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--loader=filename] [--skipresponse] [--debugmode] [--vid=vid] [--pid=pid] [--devicemodel=value] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl ws <start_sector> <filename> [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--skipwrite] [--skipresponse] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--devicemodel=value] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl e <partitionname> [--memory=memtype] [--skipwrite] [--lun=lun] [--sectorsize==bytes] [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--devicemodel=value] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl es <start_sector> <sectors> [--memory=memtype] [--lun=lun] [--sectorsize==bytes] [--skipwrite] [--loader=filename] [--skipresponse] [--debugmode] [--vid=vid] [--pid=pid] [--devicemodel=value] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl ep <partitionname> <sectors> [--memory=memtype] [--skipwrite] [--lun=lun] [--sectorsize==bytes] [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--devicemodel=value] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl footer <filename> [--memory=memtype] [--lun=lun] [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl peek <offset> <length> <filename> [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]
    edl peekhex <offset> <length> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]
    edl peekdword <offset> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl peekqword <offset> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl memtbl <filename> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl poke <offset> <filename> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl pokehex <offset> <data> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl pokedword <offset> <data> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl pokeqword <offset> <data> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl memcpy <offset> <size> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]
    edl secureboot [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl pbl <filename> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl qfp <filename> [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]
    edl getstorageinfo [--loader=filename] [--memory=memtype] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl setbootablestoragedrive <lun> [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl getactiveslot [--memory=memtype] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl setactiveslot <slot> [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl send <command> [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl xml <xmlfile> [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl rawxml <xmlstring> [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl reset [--resetmode=mode] [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl nop [--loader=filename] [--debugmode] [--vid=vid] [--pid=pid] [--skipstorageinit] [--port_name=port_name] [--serial] [--devicemodel=value]
    edl modules <command> <options> [--memory=memtype] [--lun=lun] [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--devicemodel=value] [--port_name=port_name] [--serial]
    edl provision <xmlfile> [--loader=filename] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]  [--devicemodel=value]
    edl qfil <rawprogram> <patch> <imagedir> [--loader=filename] [--memory=memtype] [--debugmode] [--skipresponse] [--vid=vid] [--pid=pid] [--port_name=port_name] [--serial]  [--devicemodel=value]

Description:
    server                      # Run tcp/ip server
    printgpt                    # Print GPT Table information
    gpt                         # Save gpt table to given directory
    r                           # Read flash to filename
    rl                          # Read all partitions from flash to a directory
    rf                          # Read whole flash to file
    rs                          # Read sectors starting at start_sector to filename
    w                           # Write filename to partition to flash
    wl                          # Write all files from directory to flash
    wf                          # Write whole filename to flash
    ws                          # Write filename to flash at start_sector
    e                           # Erase partition from flash
    es                          # Erase sectors at start_sector from flash
    ep                          # Erase sector count from flash partition
    footer                      # Read crypto footer from flash
    peek                        # Dump memory at offset with given length to filename
    peekhex                     # Dump memory at offset and given length
    peekdword                   # Dump DWORD at memory offset
    peekqword                   # Dump QWORD at memory offset
    memtbl                      # Dump memory table to file
    poke                        # Write filename to memory at offset to memory
    pokehex                     # Write hex string data at offset to memory
    pokedword                   # Write DWORD to memory at offset
    pokeqword                   # Write QWORD to memory at offset
    memcpy                      # Copy memory from srcoffset with given size to dstoffset
    secureboot                  # Print secureboot fields from qfprom fuses
    pbl                         # Dump primary bootloader to filename
    qfp                         # Dump QFPROM fuses to filename
    getstorageinfo              # Print storage info in firehose mode
    setbootablestoragedrive     # Change bootable storage drive to lun number
    send                        # Send firehose command
    xml                         # Send firehose xml file
    rawxml                      # Send firehose xml raw string
    reset                       # Send firehose reset command, reset modes: reset, off, edl
    nop                         # Send firehose nop command
    modules                     # Enable submodules, for example: "oemunlock enable"
    setactiveslot               # Set partition as active (Slot A/B)
    provision                   # UFS provision
    qfil                        # Write rawprogram xml files
                                # <rawprogram> : program config xml, such as rawprogram_unsparse.xml or rawprogram*.xml
                                # <patch> : patch config xml, such as patch0.xml or patch*.xml
                                # <imagedir> : directory name of image files

Options:
    --loader=filename                  Use specific EDL loader, disable autodetection [default: None]
    --vid=vid                          Set usb vendor id used for EDL [default: -1]
    --pid=pid                          Set usb product id used for EDL [default: -1]
    --lun=lun                          Set lun to read/write from (UFS memory only)
    --maxpayload=bytes                 Set the maximum payload for EDL [default: 0x100000]
    --sectorsize=bytes                 Set default sector size
    --memory=memtype                   Set memory type ("NAND", "eMMC", "UFS", "spinor")
    --partitionfilename=filename       Set partition table as filename for streaming mode
    --partitions=partnames             Skip reading partition with names != "partname1,partname2,etc."
    --skipwrite                        Do not allow any writes to flash (simulate only)
    --skipresponse                     Do not expect a response from phone on read/write (some Qualcomms)
    --skipstorageinit                  Skip storage initialisation
    --debugmode                        Enable verbose mode
    --gpt-num-part-entries=number      Set GPT entry count [default: 0]
    --gpt-part-entry-size=number       Set GPT entry size [default: 0]
    --gpt-part-entry-start-lba=number  Set GPT entry start lba sector [default: 0]
    --tcpport=portnumber               Set port for tcp server [default: 1340]
    --skip=partnames                   Skip reading partition with names "partname1,partname2,etc."
    --genxml                           Generate rawprogram[lun].xml
    --devicemodel=value                Set device model
    --port_name=port_name                Set serial port name (/dev/ttyUSB0 for Linux/MAC; \\\\.\\COM1 for Windows)
    --serial                           Use serial port (port autodetection)
    --slot                             Set active slot for setactiveslot [a or b]
    --resetmode=mode                   Resetmode for reset (poweroff, reset, edl, etc.)
"""

import logging
import os
import re
import subprocess
import sys
import time

from edlclient.Config.usb_ids import default_ids
from edlclient.Library.Connection.serial_lib import SerialDevice
from edlclient.Library.Connection.usblib import USBClass # TODO: AT here
from edlclient.Library.firehose_client import firehose_client
from edlclient.Library.sahara import sahara
from edlclient.Library.sahara_defs import cmd_t, sahara_mode_t
from edlclient.Library.streaming import Streaming
from edlclient.Library.streaming_client import streaming_client
from edlclient.Library.utils import LogBase
from edlclient.Library.utils import is_windows
from edlclient.Tools import null

class EDL(metaclass=LogBase):
    """ EDL类

    Args:
        args: 参数
        imported (bool) = True: 状态为独立运行(True)/模块导入(False)
        enabled_log (bool) = True: 是否开启日志功能
        enabled_print (bool) = False: 是否输出到屏幕上

    """

    def __init__(self, args, imported: bool = True, enabled_log: bool = False, enabled_print: bool = False):

        if enabled_log:
            self._logger = self._logger
            self.info = self._logger.info
            self.debug = self._logger.debug
            self.error = self._logger.error
            self.warning = self._logger.warning
        else:
            self._logger = null.NullObject()
            self.info = null.null_function
            self.debug = null.null_function
            self.error = null.null_function
            self.warning = null.null_function

        self.enabled_print = enabled_print
        self.imported = imported
        self.enabled_log = enabled_log
        self.serial = None
        self.port_name = None
        self.cdc = None
        self.sahara = None
        self.vid = None
        self.pid = None
        self.serial_number = None
        self.args = args
        self.fh = None

    def _print(self, *args, sep=' ', end='\n', file=sys.stdout, flush=False) -> None:
        """ 自定义输出函数，根据enabled_print来决定是否输出

        Args:
            *args: 输出内容
            sep = ' ': 分隔符
            end = '\n': 结尾符
            file = sys.stdout: 输出目标
            flush = False: 是否强制刷新缓冲区

        """

        if self.enabled_print:
            print(*args, sep=sep, end=end, file=file, flush=flush)

    def _stdout_write(self, text: str) -> int:
        """ sys.stdout.write函数改进版，根据enabled_print来决定是否输出

        Args:
            text (str): 文本

        Returns:
            int: 返回状态码

        """

        status = 0
        if self.enabled_print:
            status = sys.stdout.write(text)
        return status

    def _stdout_flush(self) -> None:
        """ sys.stdout.flush函数改进版，根据enabled_print来决定是否输出

        Returns:
            None

        """
        if self.enabled_print:
            sys.stdout.flush()

    def parse_cmd(self, unresolved_args: dict) -> list:
        """ 解析指令

        Args:
            unresolved_args (dict): 未解析命令

        Return:
            list: 结果

        """
        if self.imported:
            return []

        parsed_cmd = []
        cmds = ["server", "printgpt", "gpt", "r", "rl", "rf", "rs", "w", "wl", "wf", "ws", "e", "es", "ep", "footer",
                "peek", "peekhex", "peekdword", "peekqword", "memtbl", "poke", "pokehex", "pokedword", "pokeqword",
                "memcpy", "secureboot", "pbl", "qfp", "getstorageinfo", "setbootablestoragedrive", "getactiveslot",
                "setactiveslot",
                "send", "xml", "rawxml", "reset", "nop", "modules", "memorydump", "provision", "qfil"]
        for cmd in cmds:
            if unresolved_args.get(cmd, False):
                parsed_cmd.append(cmd)

        return parsed_cmd

    def console(self, cmd):
        """ 执行控制台命令

        Args:
            cmd: 控制台命令

        Return:
            str: 控制台执行后的输出

        """
        if self.enabled_print:
            process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.STDOUT,
                                       stderr=subprocess.STDOUT, text=True, close_fds=True)
        else:
            process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, close_fds=True)

        output, _ = process.communicate()
        return output

    @staticmethod
    def parse_option(unresolved_options: dict) -> dict:
        """ 解析选项

        Args:
            unresolved_options (dict): 选项

        Return:
            dict: 包含 '--' 或 '<', '>' 的选项

        """

        options = {}
        for arg in unresolved_options:
            if "--" in arg or "<" in arg:
                options[arg] = unresolved_options[arg]
        return options

    def connect(self, loop: int) -> dict:
        """ 连接设备

        Args:
            loop (int): 最大尝试次数

        Return:
            dict: 连接成功返回设备信息字典，失败返回 {"mode": "error"}

        """

        while not self.cdc.connected:
            self.cdc.connected = self.cdc.connect(port_name=self.port_name)
            if not self.cdc.connected:
                self._stdout_write('.')

                if loop == 5:
                    self._stdout_write('\n')
                    self.info("Hint:   Press and hold vol up+dwn, connect usb. For some, only use vol up.")
                    self.info("Xiaomi: Press and hold vol dwn + pwr, in fastboot mode connect usb.\n" +
                              "        Run \"./fastpwn oem edl\".")
                    self.info("Other:  Run \"adb reboot edl\".")
                    self._stdout_write('\n')

                if loop >= 20:
                    self._stdout_write('\n')
                    loop = 6
                loop += 1
                time.sleep(1)
                self._stdout_flush()
            else:
                self.info("Device detected :)")
                try:
                    resp = self.sahara.connect()
                    self.vid = self.cdc.vid
                    self.pid = self.cdc.pid
                except Exception as err:  # pylint: disable=broad-except
                    self.debug(str(err))
                    continue
                if "mode" in resp:
                    mode = resp["mode"]
                    self.info(f"Mode detected: {mode}")
                    return resp
        return {"mode": "error"}

    def exit(self, status: int = 0, cdc_close: bool = True) -> None | int:
        """ 提供可控的退出机制

        Args:
            status (int) = 0: 退出状态码
            cdc_close (bool) = True: 是否关闭 CDC 连接

        Return:
            None | int: 如果是导入模式返回状态码，否则无返回（调用系统退出）

        """

        if cdc_close:
            self.cdc.close()

        if self.imported:
            return status
        else:
            sys.exit(status)

    def run(self) -> int:
        """ 主执行方法，处理EDL设备连接、协议协商和命令执行
        
        Return:
            int: 状态码
            
        """

        if is_windows():
            proper_driver = self.console(r'reg query HKLM\HARDWARE\DEVICEMAP\SERIALCOMM')
            if re.findall(r'QCUSB', str(proper_driver)):
                self.warning(f'Please first install libusb_win32 driver from Zadig')

        loop = 0
        vid = int(self.args["--vid"], 16)
        pid = int(self.args["--pid"], 16)
        interface = -1

        if vid != -1 and pid != -1:
            port_config = [[vid, pid, interface]]
        else:
            port_config = default_ids

        if self.args["--debugmode"] and self.enabled_log:
            log_file_name = "log.txt"
            if os.path.exists(log_file_name):
                os.remove(log_file_name)
            self.fh = logging.FileHandler(log_file_name)
            self._logger.addHandler(self.fh)
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

        if self.args["--serial"]:
            self.serial = True
        else:
            self.serial = False

        if self.args["--port_name"]:
            self.port_name = self.args["--port_name"]
            self.serial = True
        else:
            self.port_name = ""

        if self.serial:
            self.cdc = SerialDevice(log_level=self._logger.level, port_config=port_config)
        else:
            if self.args["--serial_number"]:
                self.serial_number = self.args["--serial_number"]
            self.cdc = USBClass(port_config=port_config, log_level=self._logger.level, serial_number=self.serial_number)

        self.sahara = sahara(self.cdc, loglevel=self._logger.level)

        if self.args["--loader"] == 'None':
            self.info("Trying with no loader given ...")
            self.sahara.programmer = ""
        else:
            loader = self.args["--loader"]
            self.info(f"Using loader {loader} ...")
            self.sahara.programmer = loader

        self.info("Waiting for the device")
        self.cdc.timeout = 1500
        connect_info = self.connect(loop)
        mode = connect_info["mode"]
        try:
            version = connect_info.get("data").version
        except AttributeError:
            version = 2

        if mode == "sahara":
            cmd = connect_info["cmd"]
            if cmd == cmd_t.SAHARA_HELLO_REQ:
                if "data" in connect_info:
                    data = connect_info["data"]
                    if data.mode == sahara_mode_t.SAHARA_MODE_MEMORY_DEBUG:
                        if self.args["memorydump"] or self.cdc.pid == 0x900E:
                            time.sleep(0.5)
                            self._print("Device is in memory dump mode, dumping memory")
                            if self.args["--partitions"]:
                                self.sahara.debug_mode(self.args["--partitions"].split(","), version=version)
                            else:
                                self.sahara.debug_mode(version=version)
                            return self.exit()
                        else:
                            self._print("Device is in streaming mode, uploading loader")
                            self.cdc.timeout = None
                            sahara_info = self.sahara.streaminginfo()
                            if sahara_info:
                                sahara_connect = self.sahara.connect()
                                if len(sahara_connect) == 3:
                                    mode, cmd, resp = sahara_connect
                                else:
                                    mode, resp = sahara_connect
                                if mode == "sahara":
                                    mode = self.sahara.upload_loader(version=version)
                                    if "enprg" in self.sahara.programmer.lower():
                                        mode = "load_enandprg"
                                    elif "nprg" in self.sahara.programmer.lower():
                                        mode = "load_nandprg"
                                    elif mode != "":
                                        mode = "load_" + mode
                                    if "load_" in mode:
                                        time.sleep(0.3)
                                    else:
                                        self._print("Error, couldn't find suitable enprg/nprg loader :(")
                                        return self.exit()
                    else:
                        sahara_info = self.sahara.cmd_info(version=version)
                        if sahara_info is not None:
                            resp = self.sahara.connect()
                            mode = resp["mode"]
                            if "data" in resp:
                                data = resp["data"]
                            if mode == "sahara":
                                mode = self.sahara.upload_loader(version=version)
                        else:
                            self._print("Error on sahara handshake, resetting.")
                            self.sahara.cmd_reset()
                            return self.exit(1)
        else:
            if self._logger.level != logging.DEBUG:
                self._logger.setLevel(logging.ERROR)
        if mode == "error":
            self._print("Connection detected, quiting.")
            return self.exit(1)
        elif mode == "firehose":
            if "enprg" in self.sahara.programmer.lower():
                mode = "enandprg"
            elif "nprg" in self.sahara.programmer.lower():
                mode = "nandprg"
            if mode != "firehose":
                streaming = Streaming(self.cdc, self.sahara, self._logger.level)
                if streaming.connect(1):
                    self._print("Successfully uploaded programmer :)")
                    mode = "nandprg"
                else:
                    self._print("No suitable loader found :(")
                    return self.exit()
        if mode != "firehose":
            sc = streaming_client(self.args, self.cdc, self.sahara, self._logger.level, self._print)
            cmd = self.parse_cmd(self.args)
            options = self.parse_option(self.args)
            if "load_" in mode:
                options["<mode>"] = 1
            else:
                options["<mode>"] = 0
            sc.handle_streaming(cmd, options)
        else:
            self.cdc.timeout = None
            cmd = self.parse_cmd(self.args)
            if cmd == 'provision':
                self.args["--memory"] = 'ufs'
                self.args["--skipstorageinit"] = 1
            self.fh = firehose_client(self.args, self.cdc, self.sahara, self._logger.level, self._print)
            options = self.parse_option(self.args)
            if cmd != "" or self.imported:
                self.info("Trying to connect to firehose loader ...")
                if self.fh.connect(sahara):
                    if self.imported:
                        return self.exit(cdc_close=False)
                    elif not self.fh.handle_firehose(cmd, options):
                        return self.exit(1)
                else:
                    return self.exit(1)

if __name__ == "__main__":
    edl = EDL('test')
