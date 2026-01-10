#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any

from edlclient import edl

default_edl_args = {
    # -------------------------- 调试/基础配置类参数 --------------------------
    "--debugmode": False,
    # 是否启用调试模式：开启后会输出详细的EDL交互日志（如命令收发、数据解析过程），便于定位问题

    "--devicemodel": None,
    # 设备型号：指定目标高通设备的型号（如"Pixel 6"），用于匹配对应设备的EDL配置和分区表

    "--genxml": False,
    # 是否生成XML配置文件：开启后会根据当前参数自动生成EDL操作所需的XML配置（如分区烧录的rawprogram.xml）

    # -------------------------- GPT分区表配置类参数 --------------------------
    "--gpt-num-part-entries": "0",
    # GPT分区表的条目数量：指定GPT（GUID Partition Table）中分区条目的总数，0表示使用设备默认值

    "--gpt-part-entry-size": "0",
    # GPT分区条目的大小（字节）：单个GPT分区条目的长度，0表示使用设备默认的分区条目大小

    "--gpt-part-entry-start-lba": "0",
    # GPT分区条目起始LBA地址：LBA（Logical Block Address）是磁盘逻辑块地址，0表示使用设备默认起始地址

    # -------------------------- 加载器/传输配置类参数 --------------------------
    "--loader": "None",
    # EDL加载器路径：指定高通设备进入EDL模式后加载的编程器（loader）文件路径（如"prog_emmc_firehose_8998.mbn"），None表示不加载

    "--lun": None,
    # 逻辑单元号（Logical Unit Number）：指定存储设备的LUN编号（如eMMC的LUN0/1），用于区分多存储单元设备

    "--maxpayload": "0x100000",
    # 最大有效载荷大小（十六进制）：EDL传输时单次数据包的最大长度，0x100000=1MB，是高通设备的常见默认值

    # -------------------------- 设备硬件配置类参数 --------------------------
    "--memory": None,
    # 内存配置：指定设备内存类型/大小（如"8GB"），用于适配不同内存规格的设备EDL操作

    "--sectorsize": None,
    # 扇区大小（字节）：指定存储设备的物理扇区大小（如512/4096字节），None表示自动检测设备扇区大小

    "--pid": "-1",
    # USB产品ID（Product ID）：目标高通设备的USB PID，-1表示自动匹配已连接的EDL设备PID

    "--vid": "-1",
    # USB厂商ID（Vendor ID）：高通设备的USB VID（默认高通VID为0x05C6），-1表示自动匹配

    "--serial_number": None,
    # 设备序列号：指定目标设备的唯一序列号，用于区分多台同时连接的EDL设备

    # -------------------------- 连接/通信配置类参数 --------------------------
    "--port_name": None,
    # 端口名称：串口/USB端口名称（如"/dev/ttyUSB0"或"COM3"），用于指定EDL通信的物理端口

    "--serial": False,
    # 是否使用串口通信：False表示使用USB通信（EDL默认），True表示切换为串口通信

    "--tcpport": "1340",
    # TCP端口号：EDL模式下网络调试/传输的TCP端口，默认1340，用于远程EDL操作

    # -------------------------- 操作行为控制类参数 --------------------------
    "--resetmode": None,
    # 重置模式：指定EDL操作完成后的设备重置方式（如"cold"冷重启、"warm"热重启），None表示不重置

    "--skip": None,
    # 跳过操作：指定需要跳过的EDL步骤（如"storageinit"跳过存储初始化），None表示执行所有步骤

    "--skipresponse": False,
    # 是否跳过响应检查：True表示不等待设备的EDL命令响应，False表示校验每一步响应的正确性

    "--skipstorageinit": False,
    # 是否跳过存储初始化：True表示不初始化存储设备（eMMC/UFS），False表示执行存储初始化（EDL必选步骤）

    "--skipwrite": False,
    # 是否跳过写入操作：True表示仅校验数据不写入存储，False表示执行实际的烧录/写入操作

    # -------------------------- 操作对象/参数占位符（无--前缀） --------------------------
    "<command>": None,
    # EDL核心命令：指定要执行的EDL操作命令（如"flash"烧录、"read"读取、"erase"擦除、"boot"启动loader）

    "<data>": None,
    # 原始数据：用于传输的二进制原始数据（如分区补丁数据、配置参数二进制流）

    "<directory>": None,
    # 目录路径：指定文件操作的目标目录（如烧录文件所在的文件夹路径）

    "<filename>": None,
    # 文件名：指定EDL操作的目标文件（如loader文件、镜像文件、XML配置文件路径）

    "<imagedir>": None,
    # 镜像目录：指定多个镜像文件的存放目录（如批量烧录时的镜像文件夹）

    "<length>": None,
    # 数据长度：指定读取/写入的数据长度（字节），用于精准读取/写入部分分区数据

    "<lun>": None,
    # 逻辑单元号（占位符）：与--lun作用一致，作为命令行参数占位符单独传递

    "<offset>": None,
    # 偏移量：指定存储设备中的数据偏移地址（字节），用于从指定位置开始读写

    "<options>": None,
    # 扩展选项：EDL命令的扩展配置参数（如烧录时的校验选项、强制写入选项）

    "<partitionname>": None,
    # 分区名称：指定目标分区名称（如"boot"、"system"、"userdata"），用于单分区操作

    "<patch>": None,
    # 补丁文件：指定分区补丁文件路径（如用于修复分区的差分补丁）

    "<rawprogram>": None,
    # RawProgram XML文件：指定高通烧录格式的XML文件（rawprogram.xml），定义分区烧录规则

    "<sectors>": None,
    # 扇区数量：指定操作的扇区总数（如擦除100个扇区），与扇区大小配合计算数据量

    "<size>": None,
    # 大小：指定操作的数据总大小（字节/MB/GB），如读取1GB的userdata分区数据

    "<slot>": None,
    # 槽位号：安卓A/B分区槽位（如"a"、"b"），用于指定烧录/读取的分区槽位

    "<start_sector>": None,
    # 起始扇区：指定操作的起始扇区编号，与sectors配合定位操作范围

    "<xmlfile>": None,
    # XML文件路径：指定EDL操作的配置XML文件（如gpt.xml、rawprogram.xml）

    "<xmlstring>": None,
    # XML字符串：直接传递XML配置内容（无需文件），用于动态生成临时配置
}


class EDL_API:

    def __init__(self, args=None, enabled_print: bool = False, enabled_log: bool = False):
        """ EDL API类

        Args:
            args (dict) = default_edl_args: 参数配置
            enabled_print (bool) = False: 是否打印
            enabled_log (bool) = False: 是否开启日志功能:

        """
        if args is None:
            args = default_edl_args
        self.edl = None
        self.status = 0
        self.args = {**args}
        self.enabled_print = enabled_print
        self.enabled_log = enabled_log

    def init(self) -> int:
        """ 初始化EDL实例并运行

        Return:
            int: 状态码

        """
        self.edl = edl.EDL(self.args, enabled_log=self.enabled_log, enabled_print=self.enabled_print)
        self.status = self.edl.run()
        return self.status

    def del_init(self) -> int:
        """ 清理EDL实例

        Return:
            int: 状态码

        """

        if self.edl is not None:
            self.status = self.edl.exit()
            self.edl = None

        return self.status

    def reinit(self) -> int:
        """ 重新初始化EDL实例

        Return:
            int: 状态码

        """

        if self.del_init() == 0: # TODO: 原来此处为1
            return self.status
        return self.init()

    def set_arg(self, key: str, value: Any, reset: bool = False):
        """
        设置参数值

        Args:
            key (str): 参数键
            value (Any): 参数值
            reset (bool): 是否将 key 对应的值重置为默认值

        Returns:
            bool: 是否成功设置

        """

        if key not in self.args:
            return 'Invalid key!'

        if reset:
            value = default_edl_args[key]

        self.args[key] = value
        if self.edl is not None:
            self.edl.args = self.args.copy()

        return self.args

    def reset_arg(self, key: str) -> bool:
        """重置参数为默认值

        Args:
            key (str): 参数键

        Returns:
            bool: 是否成功设置

        """
        return self.set_arg(key, None, True)

    def __del__(self) -> int:
        """ 析构函数自动清理

        Return:
            int: 状态码

        """

        return self.del_init()

    # ----- Actual API -----

    def server(self):
        """启动TCP/IP服务器模式

        启动一个TCP服务器，允许通过网络连接与EDL设备通信。
        服务器默认监听端口1340，可以通过--tcpport参数修改。

        Returns:
            int: 服务器运行状态码，0表示成功，非0表示失败

        """
        return self.edl.fh.handle_firehose("server", self.edl.args)

    def memory_dump(self):
        """执行内存转储

        当设备处于内存调试模式时，转储设备内存内容。
        通常用于调试和分析设备状态。

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        return self.edl.fh.handle_firehose("memorydump", self.edl.args)

    def print_gpt(self) -> bool:
        """ 打印GPT分区表信息

        打印设备的GPT（GUID Partition Table）分区表信息，
        包括分区名称、大小、起始扇区等。

        Returns:
            bool: 指令是否执行成功

        """
        if self.enabled_print:
            return self.edl.fh.handle_firehose("printgpt", self.edl.args)
        else:
            return False

    def get_gpt(self) -> dict:
        """ 获取GPT分区表信息

        获取设备的GPT（GUID Partition Table）分区表信息，
        包括分区名称、大小、起始扇区等。

        Return:
            dict: 分区表信息

        """
        return self.edl.fh.handle_firehose("getgpt", self.edl.args)

    def gpt(self, directory: str):
        """保存GPT分区表到指定目录

        读取设备的GPT分区表，并将分区信息保存到指定目录。
        可以生成rawprogram.xml文件用于后续编程操作。

        Args:
            directory: 保存GPT信息的目录路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<directory>", directory)
        # self.edl.fh.handle_firehose("printgpt", self.edl.args)
        return self.edl.fh.handle_firehose("gpt", self.edl.args)

    def r(self, partitionname: str, filename: str):
        """读取指定分区到文件

        从设备读取指定的分区内容，并保存到本地文件。

        Args:
            partitionname: 分区名称（如"boot", "system"等）
            filename: 保存读取数据的输出文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<partitionname>", partitionname)
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose('r', self.edl.args)

    def rl(self, directory: str):
        """读取所有分区到目录

        读取设备上的所有分区，并按分区名称保存到指定目录。

        Args:
            directory: 保存分区文件的目录路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<directory>", directory)
        return self.edl.fh.handle_firehose("rl", self.edl.args)

    def rf(self, filename: str):
        """读取整个闪存到文件

        读取设备的整个闪存内容，保存到单个文件。

        Args:
            filename: 保存完整闪存镜像的输出文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("rf", self.edl.args)

    def rs(self, start_sector: str, sectors: str, filename: str):
        """读取指定扇区范围到文件

        从设备读取指定起始扇区和扇区数量的数据。

        Args:
            start_sector: 起始扇区号（16进制或10进制字符串）
            sectors: 要读取的扇区数量（16进制或10进制字符串）
            filename: 保存数据的输出文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<start_sector>", start_sector)
        self.set_arg("<sectors>", sectors)
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("rs", self.edl.args)

    def w(self, partitionname: str, filename: str):
        """写入文件到指定分区

        将本地文件内容写入到设备的指定分区。

        Args:
            partitionname: 目标分区名称
            filename: 要写入的源文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<partitionname>", partitionname)
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose('w', self.edl.args)

    def wl(self, directory: str):
        """从目录写入所有分区

         将指定目录下的所有文件写入到对应的分区。
         文件名应与分区名匹配。

         Args:
             directory: 包含分区文件的目录路径

         Returns:
             int: 操作状态码，0表示成功，非0表示失败

         """
        self.set_arg("<directory>", directory)
        return self.edl.fh.handle_firehose("wl", self.edl.args)

    def wf(self, filename: str):
        """
        写入整个闪存镜像到设备

        将本地文件中的完整闪存镜像写入到设备。

        Args:
            filename (str): 要写入的源文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("wf", self.edl.args)

    def ws(self, start_sector: str, filename: str):
        """
        写入指定扇区范围的数据到设备

        从本地文件读取数据并写入到设备的指定起始扇区。

        Args:
            start_sector (str): 起始扇区号（16进制或10进制字符串）
            filename (str): 包含要写入数据的源文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<start_sector>", start_sector)
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("ws", self.edl.args)

    def e(self, partitionname: str):
        """
        擦除指定分区

        对设备上的指定分区执行擦除操作。

        Args:
            partitionname (str): 目标分区名称

        Returns:
            int: 操作状态码，0表示成功，非0表示失败
        """

        self.set_arg("<partitionname>", partitionname)
        return self.edl.fh.handle_firehose('e', self.edl.args)

    def es(self, start_sector: str, sectors: str):
        """
        擦除指定扇区范围

        对设备上从指定起始扇区开始的连续扇区进行擦除。

        Args:
            start_sector (str): 起始扇区号（16进制或10进制字符串）
            sectors (str): 要擦除的扇区数量（16进制或10进制字符串）

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<start_sector>", start_sector)
        self.set_arg("<sectors>", sectors)
        return self.edl.fh.handle_firehose("es", self.edl.args)

    def ep(self, partitionname: str, sectors: str):
        """
        擦除指定分区的一部分

        对设备上指定分区的部分区域执行擦除操作。

        Args:
            partitionname (str): 目标分区名称
            sectors (str): 要擦除的扇区数量（16进制或10进制字符串）

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<partitionname>", partitionname)
        self.set_arg("<sectors>", sectors)
        return self.edl.fh.handle_firehose("ep", self.edl.args)

    def footer(self, filename: str):
        """
        写入分区表脚注

        将定义在文件中的分区表脚注写入到设备。

        Args:
            filename (str): 包含分区表脚注信息的文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("footer", self.edl.args)

    def peek(self, offset: int, length: int, filename: str):
        """
        读取内存数据并保存到文件

        从指定偏移地址读取一定长度的内存数据，并将其保存到文件中。

        Args:
            offset (int): 开始读取的偏移地址
            length (int): 要读取的数据长度
            filename (str): 保存读取数据的目标文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<offset>", offset)
        self.set_arg("<length>", length)
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("peek", self.edl.args)

    def peek_hex(self, offset: int, length: int):
        """
        读取内存数据并以十六进制格式打印

        从指定偏移地址读取一定长度的内存数据，并以十六进制格式打印出来。

        Args:
            offset (int): 开始读取的偏移地址
            length (int): 要读取的数据长度

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<offset>", offset)
        self.set_arg("<length>", length)
        return self.edl.fh.handle_firehose("peekhex", self.edl.args)

    def peekd_word(self, offset: int):
        """
        读取内存中的双字数据

        从指定偏移地址读取一个双字(4字节)的数据。

        Args:
            offset (int): 开始读取的偏移地址

        Returns:
            int: 读取到的双字数据

        """
        self.set_arg("<offset>", offset)
        return self.edl.fh.handle_firehose("peekdword", self.edl.args)

    def peekq_word(self, offset: int):
        """
        读取内存中的四字数据

        从指定偏移地址读取一个四字（8字节）的数据。

        Args:
            offset (int): 开始读取的偏移地址

        Returns:
            int: 读取到的四字数据

        """
        self.set_arg("<offset>", offset)
        return self.edl.fh.handle_firehose("peekqword", self.edl.args)

    def save_memory_table_to_file(self, filename: str):
        """
        读取内存表并保存到文件

        从设备读取内存表，并将其保存到指定文件中。

        Args:
            filename (str): 保存内存表的目标文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("memtbl", self.edl.args)

    def poke(self, offset: int, filename: str):
        """
        写入文件数据到内存

        从指定文件读取数据，并将其写入到设备的指定偏移地址。

        Args:
            offset (int): 写入数据的偏移地址
            filename (str): 包含要写入数据的源文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<offset>", offset)
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("poke", self.edl.args)

    def poke_hex(self, offset: int, data: str):
        """
        写入十六进制数据到内存

        将指定的十六进制数据写入到设备的指定偏移地址。

        Args:
            offset (int): 写入数据的偏移地址
            data (str): 要写入的十六进制数据

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<offset>", offset)
        self.set_arg("<data>", data)
        return self.edl.fh.handle_firehose("pokehex", self.edl.args)

    def poked_word(self, offset: int, data: str):
        """
        写入双字数据到内存

        将指定的双字（4字节）数据写入到设备的指定偏移地址。

        Args:
            offset (int): 写入数据的偏移地址
            data (str): 要写入的双字数据

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<offset>", offset)
        self.set_arg("<data>", data)
        return self.edl.fh.handle_firehose("pokedword", self.edl.args)

    def pokeq_word(self, offset: int, data: str):
        """
        写入四字数据到内存

        将指定的四字（8字节）数据写入到设备的指定偏移地址。

        Args:
            offset (int): 写入数据的偏移地址
            data (str): 要写入的四字数据

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<offset>", offset)
        self.set_arg("<data>", data)
        return self.edl.fh.handle_firehose("pokeqword", self.edl.args)

    def memory_copy(self, offset: int, size: int):
        """
        内存复制

        在内存中复制指定大小的数据块。

        Args:
            offset (int): 复制数据的起始偏移地址
            size (int): 要复制的数据大小

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<offset>", offset)
        self.set_arg("<size>", size)
        return self.edl.fh.handle_firehose("memcpy", self.edl.args)

    def secure_boot(self):
        """
        安全启动

        配置并启用设备的安全启动功能。

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        return self.edl.fh.handle_firehose("server", self.edl.args)

    def pbl(self, filename: str):
        """
        加载PBL

        从指定文件加载PBL（Primary Boot Loader）。

        Args:
            filename (str): PBL文件的路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("pbl", self.edl.args)

    def qfp(self, filename: str):
        """
        加载QFPROM

        从指定文件加载QFPROM（Qualcomm Flash PROM）。

        Args:
            filename (str): QFPROM文件的路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<filename>", filename)
        return self.edl.fh.handle_firehose("qfp", self.edl.args)

    def get_storage_info(self):
        """
        获取存储信息

        从设备获取存储器的信息。

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        return self.edl.fh.handle_firehose("getstorageinfo", self.edl.args)

    def setbootablestoragedrive(self, lun: str):
        """
        设置可启动存储驱动器

        设置指定LUN作为可启动存储驱动器。

        Args:
            lun (str): LUN号

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<lun>", lun)
        return self.edl.fh.handle_firehose("setbootablestoragedrive", self.edl.args)

    def getactiveslot(self):
        """
        获取当前活动槽位

        获取当前活动的A/B槽位。

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        return self.edl.fh.handle_firehose("getactiveslot", self.edl.args)

    def setactiveslot(self, slot: str):
        """
        获取当前活动槽位

        获取当前活动的A/B槽位。

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<slot>", slot)
        return self.edl.fh.handle_firehose("setactiveslot", self.edl.args)

    def send(self, command: str):
        """
        发送命令

        发送指定命令到设备。

        Args:
            command (str): 要发送的命令

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<command>", command)
        return self.edl.fh.handle_firehose("send", self.edl.args)

    def xml(self, xmlfile: str):
        """
        发送XML文件

        发送指定的XML文件到设备。

        Args:
            xmlfile (str): XML文件路径

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<xmlfile>", xmlfile)
        return self.edl.fh.handle_firehose("xml", self.edl.args)

    def rawxml(self, xmlstring: str):
        """
        发送XML字符串

        发送指定的XML字符串到设备。

        Args:
            xmlstring (str): XML字符串

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<xmlstring>", xmlstring)
        return self.edl.fh.handle_firehose("rawxml", self.edl.args)

    def reset(self):
        """
        重置设备

        重置设备到初始状态。

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        return self.edl.fh.handle_firehose("reset", self.edl.args)

    def nop(self):
        """
        无操作

        发送无操作命令到设备。

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        return self.edl.fh.handle_firehose("nop", self.edl.args)

    def modules(self, command: str, options: str):
        """
        模块操作

        执行模块相关的操作。

        Args:
            command (str): 模块命令
            options (str): 模块选项

        Returns:
            int: 操作状态码，0表示成功，非0表示失败

        """
        self.set_arg("<command>", command)
        self.set_arg("<options>", options)
        return self.edl.fh.handle_firehose("modules", self.edl.args)

    def provision(self, xmlfile: str):
        """
        执行provision操作，将指定的XML文件传递给Firehose处理。

        Args:
            xmlfile (str): 要传递给Firehose的XML文件路径。

        Returns:
            bool: Firehose处理结果，成功返回True，失败返回False。

        """
        self.set_arg("<xmlfile>", xmlfile)
        return self.edl.fh.handle_firehose("provision", self.edl.args)

    def qfil(self, rawprogram: str, patch: str, imagedir: str):
        """
        执行QFIL（Qualcomm Flash Image Loader）操作，用于加载和刷写设备镜像。

        Args:
            rawprogram (str): 原始程序文件路径。
            patch (str): 补丁文件路径。
            imagedir (str): 镜像文件目录路径。

        Returns:
            bool: Firehose处理结果，成功返回True，失败返回False。

        """
        self.set_arg("<rawprogram>", rawprogram)
        self.set_arg("<patch>", patch)
        self.set_arg("<imagedir>", imagedir)
        return self.edl.fh.handle_firehose("qfil", self.edl.args)
