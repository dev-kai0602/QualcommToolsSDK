#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!
import inspect
import argparse
import json
import logging
from xml.etree import ElementTree
from enum import Enum
import os, sys

from struct import unpack, pack
from binascii import hexlify, unhexlify

from edlclient.Library.utils import print_progress, read_object, write_object, LogBase
from edlclient.Library.Connection.usblib import usb_class
from edlclient.Library.Connection.serial_lib import SerialDevice
from edlclient.Library.hdlc import hdlc
from edlclient.Config.usb_ids import default_diag_vid_pid
from edlclient.Tools import null

errors = {
    1: "None",
    2: "Unknown",
    3: "Open Port Fail",
    4: "Port not open",
    5: "Buffer too small",
    6: "Read data fail",
    7: "Open file fail",
    8: "File not open",
    9: "Invalid parameter",
    10: "Send write ram failed",
    11: "Send command failed",
    12: "Offline phone failed",
    13: "Erase rom failed",
    14: "Timeout",
    15: "Go cmd failed",
    16: "Set baud_rate failed",
    17: "Say hello failed",
    18: "Write port failed",
    19: "Failed to read nv",
    20: "Failed to write nv",
    21: "Last failed but not recovery",
    22: "Backup file wasn't found",
    23: "Incorrect SPC Code",
    24: "Hello pkt isn't needed",
    25: "Not active"
}

diagerror = {
    20: "Generic error",
    21: "Bad argument",
    22: "Data too large",
    24: "Not connected",
    25: "Send pkt failed",
    26: "Receive pkt failed",
    27: "Extract pkt failed",
    29: "Open port failed",
    30: "Bad command",
    31: "Protected",
    32: "No media",
    33: "Empty",
    34: "List done"
}

nvitem_type = [
    ("item", "H"),
    ("rawdata", "128s"),
    ("status", "H")
]

subnvitem_type = [
    ("item", "H"),
    ("index", "H"),
    ("rawdata", "128s"),
    ("status", "H")
]


class FactImageReadInfo:
    """
    用于表示从FactImage读取的信息的类。

    Attributes:
        stream_state (int): 流状态，0 表示没有更多数据要发送，否则设置为 1。
        info_cluster_sent (int): 信息簇是否已发送，0 表示未发送，否则为 1。
        cluster_map_seqno (int): 簇映射页的序列号。
        cluster_data_seqno (int): 簇数据页的序列号。

    """
    fs_factimage_read_info = [
        ("stream_state", "B"),  # 0 indicates no more data to be sent, otherwise set to 1
        ("info_cluster_sent", "B"),  # 0 indicates if info_cluster was not sent, else 1
        ("cluster_map_seqno", "H"),  # Sequence number of cluster map pages
        ("cluster_data_seqno", "I")  # Sequence number of cluster data pages
    ]

    def __init__(self, stream_state: int, info_cluster_sent: int, cluster_map_seqno: int, cluster_data_seqno: int):
        """
        用于表示从FactImage读取的信息的类。

        Args:
            stream_state (int): 流状态，0 表示没有更多数据要发送，否则设置为 1。
            info_cluster_sent (int): 信息簇是否已发送，0 表示未发送，否则为 1。
            cluster_map_seqno (int): 簇映射页的序列号。
            cluster_data_seqno (int): 簇数据页的序列号。

        """
        self.stream_state = stream_state
        self.info_cluster_sent = info_cluster_sent
        self.cluster_map_seqno = cluster_map_seqno
        self.cluster_data_seqno = cluster_data_seqno

    def from_data(self, data: bytes):
        """
        从二进制数据中解析 FactImageReadInfo 对象。

        Args:
            data (bytes): 包含 FactImageReadInfo 数据的二进制数据。
            
        """
        tmp = read_object(data[0:0x10], self.fs_factimage_read_info)
        self.stream_state = tmp["stream_state"]
        self.info_cluster_sent = tmp["info_cluster_sent"]
        self.cluster_map_seqno = tmp["cluster_map_seqno"]
        self.cluster_data_seqno = tmp["cluster_data_seqno"]

    def to_data(self) -> bytes:
        """
        将 FactImageReadInfo 对象转换为二进制数据。

        Returns:
            bytes: 表示 FactImageReadInfo 对象的二进制数据。
            
        """
        data = write_object(self.fs_factimage_read_info, self.stream_state, self.info_cluster_sent,
                            self.cluster_map_seqno, self.cluster_data_seqno)
        return data


class FactoryHeader:
    """
    工厂镜像头部信息解析与封装类，用于处理设备存储（如EFS分区）中工厂镜像的元数据。

    Attributes:
        magic1 (int): 头部魔术值1，用于验证头部合法性
        magic2 (int): 头部魔术值2，用于验证头部合法性
        fact_version (int): 集群版本号（2字节无符号整数）
        version (int): 超级块版本号（2字节无符号整数）
        block_size (int): 每块包含的页数（4字节无符号整数）
        page_size (int): 页大小（字节，4字节无符号整数）
        block_count (int): 设备总块数（4字节无符号整数）
        space_limit (int): 已使用的总页数（定义映射表大小，4字节无符号整数）
        upper_data (list): 32个整数组成的列表，存储额外数据

    """

    factory_header = [
        ("magic1", "I"),
        ("magic2", "I"),
        ("fact_version", "H"),  # Version of this cluster
        # #Fields needed for the superblock
        ("version", "H"),  # Superblock version
        ("block_size", "I"),  # Pages per block.
        ("page_size", "I"),  # Page size in bytes.
        ("block_count", "I"),  # Total blocks in device.
        ("space_limit", "I"),  # Total number of used pages (defines the size of the map)
        ("upper_data", "32I")
    ]

    def __init__(self):
        self.magic1 = 0
        self.magic2 = 0
        self.fact_version = 0
        self.version = 0
        self.block_size = 0
        self.page_size = 0
        self.block_count = 0
        self.space_limit = 0
        self.upper_data = [0 * 32]

    def from_data(self, data):
        """
        从二进制数据中解析出FactoryHeader对象。

        Args:
            data (bytes): 二进制数据

        """
        tmp = read_object(data[0:0x9C], self.factory_header)
        self.magic1 = tmp["magic1"]
        self.magic2 = tmp["magic2"]
        self.fact_version = tmp["fact_version"]
        self.version = tmp["version"]
        self.block_size = tmp["block_size"]
        self.page_size = tmp["page_size"]
        self.block_count = tmp["block_count"]
        self.space_limit = tmp["space_limit"]
        self.upper_data = tmp["upper_data"]

    def to_data(self):
        """
        将FactoryHeader对象转换为二进制数据。

        Returns:
            bytes: 二进制数据

        """
        data = write_object(self.magic1, self.magic2, self.fact_version, self.version, self.block_size,
                            self.page_size, self.block_count, self.space_limit, self.upper_data)
        return data


class NVitem:
    """
    NV（Non-Volatile）项目数据封装类，用于存储和管理设备中的非易失性存储项信息。

    Attributes:
        item (int): NV项的唯一标识ID（十六进制），用于区分不同类型的NV项（如示例中nvitems.xml的id字段）
        data (bytes): NV项的原始二进制数据，存储实际的配置或参数信息
        status (int): NV项的状态标识（十六进制），可能表示项的有效性、读写权限等状态
        index (int): NV项的索引，用于在同类型NV项中区分不同实例（如多个同ID的NV项可通过索引区分）
        name (str): NV项的名称（如示例中nvitems.xml的name字段），用于直观标识NV项的用途

    """
    item: int = 0x0
    data: bytes = b""
    status: int = 0x0
    index: int = 0x0
    name: str = ""

    def __init__(self, item: int, index: int, data: bytes, status: int, name: str):
        """初始化nvitem对象，设置NV项的基本属性

        Args:
            item (int): NV项的唯一标识ID
            index (int): NV项的索引
            data (bytes): NV项的原始二进制数据
            status (int): NV项的状态标识
            name (str): NV项的名称

        """
        self.item = item
        self.index = index
        self.data = data
        self.status = status
        self.name = name


class diag_cmds(Enum):
    """
    诊断命令（Diagnostic Commands）枚举类，定义了高通（Qualcomm）诊断协议中支持的命令标识符。

    注：命令值采用十六进制表示，部分命令可能因设备型号或固件版本存在兼容性差异。
    """
    DIAG_VERNO_F = 0
    DIAG_ESN_F = 1
    DIAG_PEEKB_F = 2
    DIAG_PEEKW_F = 3
    DIAG_PEEKD_F = 4
    DIAG_POKEB_F = 5
    DIAG_POKEW_F = 6
    DIAG_POKED_F = 7
    DIAG_OUTP_F = 8
    DIAG_OUTPW_F = 9
    DIAG_INP_F = 0xA
    DIAG_INPW_F = 0xB
    DIAG_STATUS_F = 0xC
    DIAG_LOGMASK_F = 0xF
    DIAG_LOG_F = 0x10
    DIAG_NV_PEEK_F = 0x11
    DIAG_NV_POKE_F = 0x12
    DIAG_BAD_CMD_F = 0x13
    DIAG_BAD_PARM_F = 0x14
    DIAG_BAD_LEN_F = 0x15
    DIAG_BAD_MODE_F = 0x18
    DIAG_TAGRAPH_F = 0x19
    DIAG_MARKOV_F = 0x1a
    DIAG_MARKOV_RESET_F = 0x1b
    DIAG_DIAG_VER_F = 0x1c
    DIAG_TS_F = 0x1d
    DIAG_TA_PARM_F = 0x1E
    DIAG_MSG_F = 0x1f
    DIAG_HS_KEY_F = 0x20
    DIAG_HS_LOCK_F = 0x21
    DIAG_HS_SCREEN_F = 0x22
    DIAG_PARM_SET_F = 0x24
    DIAG_NV_READ_F = 0x26
    DIAG_NV_WRITE_F = 0x27
    DIAG_CONTROL_F = 0x29
    DIAG_ERR_READ_F = 0x2a
    DIAG_ERR_CLEAR_F = 0x2b
    DIAG_SER_RESET_F = 0x2c
    DIAG_SER_REPORT_F = 0x2d
    DIAG_TEST_F = 0x2e
    DIAG_GET_DIPSW_F = 0x2f
    DIAG_SET_DIPSW_F = 0x30
    DIAG_VOC_PCM_LB_F = 0x31
    DIAG_VOC_PKT_LB_F = 0x32
    DIAG_ORIG_F = 0x35
    DIAG_END_F = 0x36
    DIAG_SW_VERSION_F = 0x38
    DIAG_DLOAD_F = 0x3a
    DIAG_TMOB_F = 0x3b
    DIAG_STATE_F = 0x3f
    DIAG_PILOT_SETS_F = 0x40
    DIAG_SPC_F = 0x41
    DIAG_BAD_SPC_MODE_F = 0x42
    DIAG_PARM_GET2_F = 0x43
    DIAG_SERIAL_CHG_F = 0x44
    DIAG_PASSWORD_F = 0x46
    DIAG_BAD_SEC_MODE_F = 0x47
    DIAG_PR_LIST_WR_F = 0x48
    DIAG_PR_LIST_RD_F = 0x49
    DIAG_SUBSYS_CMD_F = 0x4b
    DIAG_FEATURE_QUERY_F = 0x51
    DIAG_SMS_READ_F = 0x53
    DIAG_SMS_WRITE_F = 0x54
    DIAG_SUP_FER_F = 0x55
    DIAG_SUP_WALSH_CODES_F = 0x56
    DIAG_SET_MAX_SUP_CH_F = 0x57
    DIAG_PARM_GET_IS95B_F = 0x58
    DIAG_FS_OP_F = 0x59
    # DIAG_RAM_RW_F = 0x59
    DIAG_AKEY_VERIFY_F = 0x5A
    # DIAG_CPU_RW_F = 0x5a
    DIAG_BMP_HS_SCREEN_F = 0x5b
    DIAG_CONFIG_COMM_F = 0x5c
    DIAG_EXT_LOGMASK_F = 0x5d
    DIAG_EVENT_REPORT_F = 0x60
    DIAG_STREAMING_CONFIG_F = 0x61
    DIAG_PARM_RETRIEVE_F = 0x62
    DIAG_STATUS_SNAPSHOT_F = 0x63
    DIAG_RPC_F = 0x64
    DIAG_GET_PROPERTY_F = 0x65
    DIAG_PUT_PROPERTY_F = 0x66
    DIAG_GET_GUID_F = 0x67
    DIAG_USER_CMD_F = 0x68
    DIAG_GET_PERM_PROPERTY_F = 0x69
    DIAG_PUT_PERM_PROPERTY_F = 0x6a
    DIAG_PERM_USER_CMD_F = 0x6b
    DIAG_GPS_SESS_CTRL_F = 0x6c
    DIAG_GPS_GRID_F = 0x6d
    DIAG_GPS_STATISTICS_F = 0x6E
    DIAG_TUNNEL_F = 0x6f
    DIAG_MAX_F = 0x70
    DIAG_SET_FTM_TEST_MODE = 0x72
    DIAG_EXT_BUILD_ID_F = 0x7c


class efs_cmds(Enum):
    """
     EFS（Embedded File System）诊断命令枚举类，定义了嵌入式文件系统交互的标准命令标识符。

     注：命令值为整数标识，部分命令（如EFS2_DIAG_PUT_DEPRECATED、EFS2_DIAG_GET_DEPRECATED）已过时，
     建议使用其替代命令（EFS2_DIAG_PUT、EFS2_DIAG_GET）。
     """
    # 基础交互类命令
    EFS2_DIAG_HELLO = 0
    """
    参数协商数据包（Parameter negotiation packet）
    - 功能：建立EFS诊断会话的首个命令，用于客户端与设备协商通信参数（如数据传输大小、版本兼容等）
    - 交互逻辑：客户端发送HELLO包，设备返回支持的参数集，完成会话初始化
    """

    EFS2_DIAG_QUERY = 1
    """
    EFS2参数信息查询（Send information about EFS2 params）
    - 功能：获取设备端EFS2文件系统的核心配置参数
    - 返回内容：包括文件系统版本、块大小、页大小、最大文件数、支持的功能集等元数据
    """

    # 文件操作类命令
    EFS2_DIAG_OPEN = 2
    """
    打开文件（Open a file）
    - 功能：打开指定路径的文件/设备节点，获取文件描述符（fd）
    - 参数：文件路径、打开模式（只读/只写/读写/追加等）、权限掩码
    - 返回：有效文件描述符（成功）或错误码（失败，如文件不存在、权限不足）
    """

    EFS2_DIAG_CLOSE = 3
    """
    关闭文件（Close a file）
    - 功能：关闭已打开的文件描述符，释放系统资源
    - 参数：文件描述符（fd）
    - 注意：未调用该命令可能导致文件句柄泄漏，影响后续文件操作
    """

    EFS2_DIAG_READ = 4
    """
    读取文件（Read a file）
    - 功能：从已打开的文件描述符中读取指定长度的二进制数据
    - 参数：文件描述符、读取偏移量、读取长度
    - 返回：读取的二进制数据（成功）或空数据+错误码（失败，如偏移量越界）
    """

    EFS2_DIAG_WRITE = 5
    """
    写入文件（Write a file）
    - 功能：向已打开的文件描述符写入指定二进制数据
    - 参数：文件描述符、写入偏移量、待写入二进制数据
    - 返回：实际写入的字节数（成功）或错误码（失败，如磁盘满、只读模式）
    """

    EFS2_DIAG_UNLINK = 8
    """
    删除文件/符号链接（Remove a symbolic link or file）
    - 功能：删除指定路径的普通文件或符号链接（不支持目录删除）
    - 参数：文件/链接路径
    - 注意：删除前需确保文件未被打开，否则可能删除失败
    """

    EFS2_DIAG_RENAME = 14
    """
    重命名文件/目录（Rename a file or directory）
    - 功能：修改文件/目录的路径或名称
    - 参数：原路径、目标路径
    - 注意：目标路径已存在时会覆盖（需设备端EFS支持覆盖模式）
    """

    EFS2_DIAG_TRUNCATE = 40
    """
    按文件名截断文件（Truncate a file by the name）
    - 功能：将指定路径的文件截断为指定长度（长度为0则清空文件）
    - 参数：文件路径、目标长度
    - 区别：无需提前打开文件，直接通过路径操作
    """

    EFS2_DIAG_FTRUNCATE = 41
    """
    按文件描述符截断文件（Truncate a file by a descriptor）
    - 功能：将已打开的文件截断为指定长度
    - 参数：文件描述符、目标长度
    - 优势：避免路径重复解析，效率高于TRUNCATE命令
    """

    # 链接操作类命令
    EFS2_DIAG_SYMLINK = 6
    """
    创建符号链接（Create a symbolic link）
    - 功能：为指定文件/目录创建软链接（符号链接）
    - 参数：源文件路径、链接文件路径
    - 注意：EFS2仅支持文件级符号链接，不支持目录硬链接
    """

    EFS2_DIAG_READLINK = 7
    """
    读取符号链接（Read a symbolic link）
    - 功能：获取符号链接指向的原始文件/目录路径
    - 参数：链接文件路径
    - 返回：原始路径字符串（成功）或错误码（失败，如链接无效）
    """

    # 目录操作类命令
    EFS2_DIAG_MKDIR = 9
    """
    创建目录（Create a directory）
    - 功能：在指定路径创建单层目录
    - 参数：目录路径、目录权限掩码
    - 注意：父目录不存在时创建失败，需逐级创建
    """

    EFS2_DIAG_RMDIR = 10
    """
    删除目录（Remove a directory）
    - 功能：删除指定的空目录
    - 参数：目录路径
    - 限制：目录非空时删除失败，需先删除目录内文件/子目录
    """

    EFS2_DIAG_OPENDIR = 11
    """
    打开目录（Open a directory for reading）
    - 功能：打开指定目录，获取目录描述符（dd）
    - 参数：目录路径
    - 返回：目录描述符（成功）或错误码（失败，如目录不存在）
    """

    EFS2_DIAG_READDIR = 12
    """
    读取目录（Read a directory）
    - 功能：从已打开的目录描述符中读取目录项（文件/子目录列表）
    - 参数：目录描述符、读取偏移量
    - 返回：目录项列表（包含名称、类型、大小等信息）
    """

    EFS2_DIAG_CLOSEDIR = 13
    """
    关闭目录（Close an open directory）
    - 功能：关闭已打开的目录描述符，释放目录操作资源
    - 参数：目录描述符
    """

    EFS2_DIAG_DELTREE = 37
    """
    删除目录树（Delete a Directory Tree）
    - 功能：递归删除指定目录及其下所有文件/子目录
    - 参数：根目录路径
    - 注意：高危操作，执行前需确认路径正确性，避免误删系统目录
    """

    # 文件属性/权限类命令
    EFS2_DIAG_STAT = 15
    """
    获取文件属性（Obtain information about a named file）
    - 功能：通过文件路径查询文件元数据
    - 返回：文件大小、创建时间、修改时间、权限、所有者、文件类型等
    """

    EFS2_DIAG_LSTAT = 16
    """
    获取符号链接属性（Obtain information about a symbolic link）
    - 功能：查询符号链接文件本身的属性（区别于STAT：STAT会解析链接指向的文件）
    - 返回：链接文件的元数据（而非源文件）
    """

    EFS2_DIAG_FSTAT = 17
    """
    获取文件描述符属性（Obtain information about a file descriptor）
    - 功能：通过已打开的文件描述符查询文件属性
    - 优势：无需重复解析文件路径，效率更高
    """

    EFS2_DIAG_CHMOD = 18
    """
    修改文件权限（Change file permissions）
    - 功能：修改指定文件/目录的访问权限（如读/写/执行权限）
    - 参数：文件/目录路径、新权限掩码（如0o644）
    """

    EFS2_DIAG_ACCESS = 20
    """
    检查文件可访问性（Check a named file for accessibility）
    - 功能：验证当前会话是否有权限访问指定文件（读/写/执行）
    - 参数：文件路径、访问权限类型（读/写/执行）
    - 返回：0（有权限）或非0错误码（无权限/文件不存在）
    """

    EFS2_DIAG_CHOWN = 30
    """
    修改文件所有者（Change ownership）
    - 功能：修改文件/目录的属主（UID）和属组（GID）
    - 参数：文件路径、新UID、新GID
    - 限制：需设备端EFS支持权限管理，且会话拥有管理员权限
    """

    # 文件系统信息类命令
    EFS2_DIAG_STATFS = 19
    """
    获取文件系统基础信息（Obtain file system information）
    - 功能：查询EFS2文件系统的整体状态
    - 返回：总容量、已用容量、可用容量、块大小、总块数、空闲块数等
    """

    EFS2_DIAG_NAND_DEV_INFO = 21
    """
    获取NAND设备信息（Get NAND device info）
    - 功能：查询底层NAND闪存设备的硬件参数
    - 返回：页大小、块大小、坏块数、擦除次数、设备型号等
    """

    EFS2_DIAG_STATVFS_V2 = 42
    """
    获取文件系统扩展信息（Obtains extensive file system info）
    - 功能：STATFS的增强版本，返回更详细的文件系统统计数据
    - 扩展内容：inode总数/空闲数、文件最大长度、挂载标志、保留块数等
    """

    # 工厂镜像操作类命令
    EFS2_DIAG_FACT_IMAGE_START = 22
    """
    启动工厂镜像数据输出（Start data output for Factory Image）
    - 功能：初始化工厂镜像（Factory Image）的读取流程
    - 参数：镜像分区标识、读取起始偏移
    - 作用：通知设备准备镜像数据，为后续READ命令做准备
    """

    EFS2_DIAG_FACT_IMAGE_READ = 23
    """
    读取工厂镜像数据（Get data for Factory Image）
    - 功能：分段读取工厂镜像的二进制数据
    - 参数：读取长度
    - 返回：镜像二进制数据块（长度≤请求长度），返回空表示读取完成
    """

    EFS2_DIAG_FACT_IMAGE_END = 24
    """
    结束工厂镜像数据输出（End data output for Factory Image）
    - 功能：终止工厂镜像读取流程，释放镜像操作资源
    - 注意：必须调用该命令，否则设备会维持镜像读取状态，影响其他操作
    """

    EFS2_DIAG_PREP_FACT_IMAGE = 25
    """
    准备工厂镜像导出（Prepare file system for image dump）
    - 功能：预处理EFS文件系统，确保工厂镜像导出的完整性
    - 操作：同步未写入磁盘的数据、锁定关键文件、检查文件系统一致性
    """

    # EFS项文件操作类命令
    EFS2_DIAG_PUT_DEPRECATED = 26
    """
    写入EFS项文件（Write an EFS item file）【已废弃】
    - 功能：早期版本的EFS项文件写入命令
    - 替代方案：使用EFS2_DIAG_PUT（38）命令，兼容性更好
    """

    EFS2_DIAG_GET_DEPRECATED = 27
    """
    读取EFS项文件（Read an EFS item file）【已废弃】
    - 功能：早期版本的EFS项文件读取命令
    - 替代方案：使用EFS2_DIAG_GET（39）命令，支持有序读取
    """

    EFS2_DIAG_PUT = 38
    """
    有序写入EFS项文件（Write a EFS item file in order）
    - 功能：按指定顺序写入EFS配置项文件（如NV参数文件）
    - 参数：项标识、写入偏移、二进制数据
    - 优势：相比废弃版本，支持分段有序写入，避免数据错乱
    """

    EFS2_DIAG_GET = 39
    """
    有序读取EFS项文件（Read a EFS item file in order）
    - 功能：按指定顺序读取EFS配置项文件
    - 参数：项标识、读取偏移、读取长度
    - 优势：支持断点续读，适合大尺寸配置项读取
    """

    # 错误与扩展类命令
    EFS2_DIAG_ERROR = 28
    """
    发送EFS错误数据包（Send an EFS Error Packet back through DIAG）
    - 功能：设备端向客户端反馈EFS操作的错误信息
    - 包含内容：错误码、错误描述、出错命令、出错参数等
    """

    EFS2_DIAG_EXTENDED_INFO = 29
    """
    获取扩展信息（Get Extra information）
    - 功能：查询EFS2的扩展功能与状态信息
    - 返回：支持的命令集、最大传输单元、错误码定义、版本补丁信息等
    """

    # 性能测试类命令
    EFS2_DIAG_BENCHMARK_START_TEST = 31
    """
    启动性能测试（Start Benchmark）
    - 功能：触发EFS2文件系统性能测试（读/写/擦除速度）
    - 参数：测试类型（读/写）、测试数据长度、测试次数
    """

    EFS2_DIAG_BENCHMARK_GET_RESULTS = 32
    """
    获取性能测试结果（Get Benchmark Report）
    - 功能：读取性能测试的统计数据
    - 返回：平均速度、最大/最小速度、延迟、成功率等
    """

    EFS2_DIAG_BENCHMARK_INIT = 33
    """
    初始化/重置性能测试（Init/Reset Benchmark）
    - 功能：重置性能测试环境，清除历史测试数据
    - 作用：确保每次测试的独立性，避免历史数据干扰
    """

    # 配额与预留类命令
    EFS2_DIAG_SET_RESERVATION = 34
    """
    设置组预留空间（Set group reservation）
    - 功能：为指定用户组预留EFS存储空间（防止空间被占满）
    - 参数：组ID、预留空间大小（字节）
    """

    EFS2_DIAG_SET_QUOTA = 35
    """
    设置组配额（Set group quota）
    - 功能：限制指定用户组的EFS存储空间上限
    - 参数：组ID、配额上限（字节）
    - 注意：配额小于已使用空间时，组内无法写入新数据
    """

    EFS2_DIAG_GET_GROUP_INFO = 36
    """
    获取组配额/预留信息（Retrieve Q&R values）
    - 功能：查询指定用户组的配额（Quota）和预留（Reservation）配置
    - 返回：组ID、配额上限、已用空间、预留空间、剩余空间等
    """


O_RDONLY = 0
O_WRONLY = 1
O_RDWR = 2
O_ACCMODE = O_RDONLY | O_WRONLY | O_RDWR
FS_DIAG_MAX_READ_REQ = 1024


# define DIAG_NV_WRITE_F 0x27
# define DIAG_NV_READ_F 0x26

class QualcommDiagClient(metaclass=LogBase):
    """
    高通诊断客户端类，用于通过诊断协议与高通设备进行交互。
    支持NV项读写、EFS文件系统操作、模式切换等核心功能。

    """

    def __init__(self, port_config, ep_in: int = -1, ep_out: int = -1, loglevel: int = logging.DEBUG,
                 encoding: str = 'utf-8', enabled_print: bool = False, enabled_log: bool = False):
        """
        初始化诊断客户端

        Args:
            port_config: 端口配置信息（串口号或USB设备信息）
            ep_in: USB输入端点编号（默认-1表示自动选择）
            ep_out: USB输出端点编号（默认-1表示自动选择）
            loglevel: 日志级别（默认DEBUG）
            encoding: 编码格式（默认utf-8）
            enabled_print: 是否启用打印输出
            enabled_log: 是否启用日志记录

        """
        self.hdlc = None
        self.cdc = None
        self.port_config = port_config
        self.nv_list = {}
        self.ep_in = ep_in
        self.ep_out = ep_out
        self.port_name = ""
        self.enabled_print = enabled_print
        self.enabled_log = enabled_log
        self.encoding = encoding

        if self.enabled_log:
            self._logger.setLevel(loglevel)
            
            if loglevel == logging.DEBUG:
                log_path = "log.txt"
                fh = logging.FileHandler(log_path, encoding=self.encoding)
                self._logger.addHandler(fh)

        # 获取当前脚本的绝对目录
        current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

        # 定义可能的nvitems.xml路径（优先检查父目录，再检查当前目录）
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(current_dir)), "edlclient", "Config", "nvitems.xml"),
            os.path.join(current_dir, "edlclient", "Config", "nvitems.xml")
        ]

        # 尝试从可能的路径中加载XML文件
        for xml_path in possible_paths:
            try:
                e = ElementTree.parse(xml_path).getroot()
                break
            except FileNotFoundError:
                continue  # 路径不存在，尝试下一个
            except Exception as e:
                # 捕获XML解析等其他异常，明确错误信息
                raise RuntimeError(f"解析XML文件失败（路径：{xml_path}）：{str(e)}")
        else:
            # 所有路径均未找到文件
            raise FileNotFoundError(f"未找到nvitems.xml，尝试过的路径：{possible_paths}")

        for atype in e.findall("nv"):
            name = atype.get("name")
            identifier = int(atype.get("id"))
            self.nv_list[identifier] = name

    @staticmethod
    def data_to_hex_ascii(data) -> str:
        """
        将二进制数据转换为十六进制和ASCII混合的可读格式

        Args:
            data: 二进制数据

        Returns:
            格式化的字符串

        """
        recv = ""
        plain = ""
        if len(data) == 0:
            return ""
        for i in range(len(data)):
            inf = "%02X " % data[i]
            recv += inf
            if data[i] == 0x0D or data[i] == 0x0A or (0x20 <= data[i] <= 0x9A):
                plain += chr(data[i])
            else:
                plain += " "
            if ((i + 1) % 16) == 0:
                recv += "\n"
                plain += "\n"
        res = recv + "\n-----------------------------------------------\n"
        if len(plain.replace(" ", "").replace("\n", "")) > 0:
            res += plain
        return res

    @staticmethod
    def decode_status(data) -> str:
        """
        解析状态码为可读描述

        Args:
            data: 包含状态码的响应数据

        Returns:
            状态描述字符串

        """
        info = data[0]
        if info == 0x13:
            return "Invalid Command Response"
        elif info == 0x14:
            return "Invalid parameter Response"
        elif info == 0x15:
            return "Invalid packet length Response"
        elif info == 0x17:
            return "Send Security Mode"
        elif info == 0x18:
            return "Packet not allowed in this mode ( online vs offline )"
        elif info == 0x42:
            return "Invalid nv_read/write because SP is locked"
        elif info == diag_cmds.DIAG_BAD_SEC_MODE_F.value:
            return "Security privileges required"
        else:
            return "Command accepted"

    def connect(self, serial: bool = False) -> bool:
        """
        建立与设备的连接

        Args:
            serial (bool): 是否使用串口连接（False表示USB连接）

        Returns:
            连接成功返回True，否则返回False

        """
        if serial:
            self.cdc = SerialDevice(self._logger.level if self.enabled_log else logging.DEBUG, port_config=self.port_config) # TODO: 查看serial_class
        else:
            self.cdc = usb_class(port_config=self.port_config, log_level=self._logger.level if self.enabled_log else logging.DEBUG) # TODO: 查看usb_class
        if self.cdc.connect(self.ep_in, self.ep_out, self.port_name):
            self.hdlc = hdlc(self.cdc)
            data = self.hdlc.receive_reply(timeout=0)
            return True
        return False

    def disconnect(self):
        """断开与设备的连接"""
        self.cdc.close(True)

    def send(self, cmd): # TODO: 完善注解
        """
        发送命令到设备

        Args:
            cmd: 要发送的命令字节流

        Returns:
            设备响应数据

        """
        if self.hdlc is not None:
            return self.hdlc.send_cmd_np(cmd)
        return None

    def cmd_info(self) -> str:
        """获取命令信息并格式化输出"""
        reply = self.send(b"\x00")
        return self.data_to_hex_ascii(reply)

    def enforce_crash(self):
        """强制设备崩溃（用于调试）"""
        # ./diag.py -nvwrite 1027,01 enable adsp log NV_MDSP_MEM_DUMP_ENABLED_I
        # ./diag.py -nvwrite 4399,01 enable download on reboot NV_DETECT_HW_RESET_I
        res = self.send(b"\x4B\x25\x03\x00")
        if self.enabled_print:
            print(self.decode_status(res))
        return self.decode_status(res)

    def enter_downloadmode(self):
        """进入下载模式"""
        res = self.send(b"\x3A")
        print(self.decode_status(res))

    def enter_saharamode(self) -> bool:
        """进入Sahara模式（EDL模式）

            Return:
                bool: 是否成功

        """
        self.hdlc.receive_reply(timeout=0)
        res = self.send(b"\x4b\x65\x01\x00")
        success: bool = False

        if self.enabled_print:
            if res[0] == 0x4b:
                print("Done, switched to edl") # 已切换到EDL模式
                success = True
            else:
                print("Error switching to edl. Try again.") # 切换到EDL模式失败，请重试
                success = True
        self.disconnect()

        return success

    def send_sp(self, sp: str = "FFFFFFFFFFFFFFFFFFFE"): # TODO: 完善注解
        """
        发送安全密码（SP）

        Args:
            sp (str): 安全密码（默认"FFFFFFFFFFFFFFFFFFFE"）

        Returns:
            设备响应

        """
        if isinstance(sp, str):
            sp = unhexlify(sp)
        else:
            sp = bytes(sp)

        if len(sp) < 8:
            if self.enabled_print:
                print("SP length must be 8 bytes") # SP长度必须为8字节
            return False

        res = self.send(b"\x46" + sp)  # 对应DIAG_PASSWORD_F命令
        if res[0] != 0x46:
            res = self.send(b"\x25" + sp)

        elif res[0] == 0x46:
            if res[1] == 0x0:
                if self.enabled_print:
                    print("Security Password is wrong") # 安全密码错误
            elif res[1] == 0x1:
                if self.enabled_print:
                    print("Security Password accepted.") # 安全密码已接受

        elif res[0] != 0x25:
            if self.enabled_print:
                print(self.decode_status(res))

        return res

    def send_spc(self, spc: str = "303030303030"):
        """
        发送服务编程代码（SPC）

        Args:
            spc: 服务编程代码（默认"303030303030"，即"000000"）

        Returns:
            设备响应

        """
        if isinstance(spc, str):
            spc = unhexlify(spc)
        else:
            spc = bytes(spc)

        if len(spc) < 6:
            if self.enabled_print:
                print("SPC length must be 6 bytes") # SPC长度必须为6字节
            return False

        res = self.send(b"\x41" + spc) # 对应DIAG_SPC_F命令
        if res[0] != 0x41:
            print(self.decode_status(res))
        else:
            if res[1] == 0x0:
                print("SPC is wrong") # SPC错误
            elif res[1] == 0x1:
                print("SPC accepted.") # SPC已接受
        return res

    @staticmethod
    def decode_nvitems(nvitem):
        """
        解析NV项状态码

        Args:
            nvitem: NV项对象

        Returns:
            状态描述字符串

        """
        match nvitem.status:
            case 0x1:
                return "Internal DMSS use"
            case 0x2:
                return "Unrecognized command"
            case 0x3:
                return "NV memory full"
            case 0x4:
                return "Command failed"
            case 0x5:
                return "Inactive Item"
            case 0x6:
                return "Bad Parameter"
            case 0x7:
                return "Item was read-only"
            case 0x8:
                return "Item not defined for this target"
            case 0x9:
                return "No more free memory"
            case 0xA:
                return "Internal use"
            case 0x0:
                return "OK"
            case _:
                return ""

    def print_nvitem(self, item): # TODO: 完善注解
        """
        打印指定NV项的信息

        Args:
            item: NV项ID

        """
        if self.enabled_print:
            res, nvitem = self.read_nvitem(item)
            if res:
                info = self.decode_nvitems(nvitem)
                if res:
                    if nvitem.name != "":
                        item_number = f"{hex(item)} ({nvitem.name}): "
                    else:
                        item_number = hex(item) + ": "
                    returnanswer = "NVItem " + item_number + info
                    print(returnanswer)
                    if nvitem.status == 0:
                        print("-----------------------------------------")
                        print(self.data_to_hex_ascii(nvitem.data))
                else:
                    print(nvitem)
            else:
                print(nvitem)

    def print_sub_nvitem(self, item, index: int): # TODO: 完善注解
        """
        打印指定子NV项的信息(当enabled_print为True时)

        Args:
            item: NV项ID
            index (int): 子项索引

        """
        if self.enabled_print:
            res, nvitem = self.read_nvitemsub(item, index)
            info = self.decode_nvitems(nvitem)
            if res:
                if nvitem.name != "":
                    ItemNumber = f"{hex(item), hex(index)} ({nvitem.name}): "
                else:
                    ItemNumber = hex(item) + "," + hex(index) + ": "
                returnanswer = "NVItem " + ItemNumber + info
                print(returnanswer)
                if nvitem.status == 0:
                    print("-----------------------------------------")
                    print(self.data_to_hex_ascii(nvitem.data))
            else:
                print(nvitem)

    def backup_nvitems(self, filename: str, errorlog: str = ""): # TODO: log和print需处理
        """
        备份所有NV项到文件

        Args:
            filename: 备份文件路径
            errorlog: 错误日志文件路径（为空则打印到控制台）

        """
        if not self.enabled_print:
            print = null.null_print

        nvitems = []
        pos = 0
        old = 0
        _errors = ""
        print("Dumping nvitems 0x0 to 0xFFFF.")
        for item in range(0, 0xFFFF):
            prog = int(float(pos) / float(0xFFFF) * float(100))
            if prog > old:
                print_progress(prog, 100, prefix="Progress:", suffix=f"Complete, item {hex(item)}", bar_length=50)
                old = prog
            res, nvitem = self.read_nvitem(item)
            if res:
                if nvitem.status != 0x5:
                    nvitem.status = self.decode_nvitems(nvitem)
                    nvitems.append(dict(id=nvitem.item, name=nvitem.name, data=hexlify(nvitem.data).decode("utf-8"),
                                        status=nvitem.status))
            else:
                _errors += nvitem + "\n"
            pos += 1
        js = json.dumps(nvitems)
        with open(filename, "w") as write_handle:
            write_handle.write(js)
        if errorlog == "":
            print(_errors)
        else:
            with open(errorlog, "w") as write_handle:
                write_handle.write(_errors)
        print("Done.")

    def unpackdata(self, data):
        rlen = len(data)
        idx = rlen - 1
        for i in range(0, rlen):
            byte = data[rlen - i - 1]
            if byte != 0:
                break
            idx = rlen - i - 1
        return data[:idx]

    def read_nvitem(self, item):
        rawdata = 128 * b"\x00"
        status = 0x0000
        nvrequest = b"\x26" + write_object(nvitem_type, item, rawdata, status)["raw_data"]
        data = self.send(nvrequest)
        if len(data) == 0:
            data = self.send(nvrequest)
        if len(data) > 0:
            if data[0] == 0x26:
                res = read_object(data[1:], nvitem_type)
                name = ""
                if item in self.nv_list:
                    name = self.nv_list[item]
                data = self.unpackdata(res["rawdata"])
                res = NVitem(res["item"], 0, data, res["status"], name)
                return [True, res]
            elif data[0] == 0x14:
                return [False, f"Error 0x14 trying to read nvitem {hex(item)}."]
            else:
                return [False, f"Error {hex(data[0])} trying to read nvitem {hex(item)}."]
        return [False, f"Empty request for nvitem {hex(item)}"]

    def read_nvitemsub(self, item, index):
        rawdata = 128 * b"\x00"
        status = 0x0000
        nvrequest = b"\x4B\x30\x01\x00" + write_object(subnvitem_type, item, index, rawdata, status)["raw_data"]
        data = self.send(nvrequest)
        if len(data) == 0:
            data = self.send(nvrequest)
        if len(data) > 0:
            if data[0] == 0x4B:
                res = read_object(data[4:], subnvitem_type)
                name = ""
                if item in self.nv_list:
                    name = self.nv_list[item]
                data = self.unpackdata(res["rawdata"])
                res = NVitem(res["item"], index, data, res["status"], name)
                return [True, res]
            elif data[0] == 0x14:
                return [False, f"Error 0x14 trying to read nvitem {hex(item)}."]
            else:
                return [False, f"Error {hex(data[0])} trying to read nvitem {hex(item)}."]
        return [False, f"Empty request for nvitem {hex(item)}"]

    def convertimei(self, imei):
        data = imei[0] + "A"
        for i in range(1, len(imei), 2):
            data += imei[i + 1]
            data += imei[i]
        return unhexlify("08" + data)

    def write_imei(self, imeis):
        if "," in imeis:
            imeis = imeis.split(",")
        else:
            imeis = [imeis]
        index = 0
        for imei in imeis:
            data = self.convertimei(imei)
            if index == 0:
                if not self.write_nvitem(550, data):
                    self.write_nvitemsub(550, index, data)
            else:
                self.write_nvitemsub(550, index, data)
            index += 1

    def write_nvitem(self, item, data):
        rawdata = bytes(data)
        while len(rawdata) < 128:
            rawdata += b"\x00"
        status = 0x0000
        nvrequest = b"\x27" + write_object(nvitem_type, item, rawdata, status)["raw_data"]
        res = self.send(nvrequest)
        if len(res) > 0:
            if res[0] == 0x27:
                res, nvitem = self.read_nvitem(item)
                if not res:
                    print(f"Error while writing nvitem {hex(item)} data, %s" % data)
                else:
                    if nvitem.data != data:
                        print(f"Error while writing nvitem {hex(item)} data, verified data doesn't match")
                    else:
                        print(f"Successfully wrote nvitem {hex(item)}.")
                        return True
                return False
            else:
                print(f"Error while writing nvitem {hex(item)} data, %s" % data)

    def write_nvitemsub(self, item, index, data):
        rawdata = bytes(data)
        while len(rawdata) < 128:
            rawdata += b"\x00"
        status = 0x0000
        nvrequest = b"\x4B\x30\x02\x00" + write_object(subnvitem_type, item, index, rawdata, status)["raw_data"]
        res = self.send(nvrequest)
        if len(res) > 0:
            if res[0] == 0x4B:
                res, nvitem = self.read_nvitemsub(item, index)
                if not res:
                    print(f"Error while writing nvitem {hex(item)} index {hex(index)} data, %s" % data)
                else:
                    if nvitem.data != data:
                        print(
                            f"Error while writing nvitem {hex(item)} index {hex(index)} data, verified data doesn't match")
                    else:
                        print(f"Successfully wrote nvitem {hex(item)} index {hex(index)}.")
                        return True
                return False
            else:
                print(f"Error while writing nvitem {hex(item)} index {hex(index)} data, %s" % data)

    def efsread(self, filename):
        alternateefs = b"\x4B\x3E\x19\x00"
        standardefs = b"\x4B\x13\x19\x00"
        resp = self.send(alternateefs)
        if resp[0] == 0x4B:
            efsmethod = 0x3E
        else:
            resp = self.send(standardefs)
            if resp[0] == 0x4B:
                efsmethod = 0x13
            else:
                print("No known efs method detected for reading.")
                return

        if filename == "":
            return False
        write_handle = open(filename, "wb")
        if write_handle is None:
            print("Error on writing file ....")
            return False

        print("Reading EFS ....")
        fefs = FactImageReadInfo(0, 0, 0, 0)

        # EFS Cmd
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_PREP_FACT_IMAGE.value, 0x00)  # prepare factory image

        resp = self.send(buf)
        if len(resp) == 0:
            print("Phone does not respond. Maybe another software is blocking the port.")
            return False

        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_FACT_IMAGE_START.value,
                   0x00)  # indicate start read out factory image

        resp = self.send(buf)

        # EFS Cmd
        buf = pack("<BBBBBBHI", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_FACT_IMAGE_READ.value, 0x00, fefs.stream_state,
                   fefs.info_cluster_sent,
                   fefs.cluster_map_seqno, fefs.cluster_data_seqno)

        resp = self.send(buf)
        if resp == 0 or resp == -1:
            info = ("Page %08X error !\n" % fefs.cluster_data_seqno)
            print(info)
            resp = self.send(buf)
            if resp == 0 or resp == -1:
                print("Data Error occured, ") + info

        error = unpack("<I", resp[4:8])[0]

        if (resp[0] == 0x13) or (resp[0] == 0x14) or (resp[0] == 0x15) or (error != 0x0):
            print("EFS Read not supported by phone. Aborting")
            write_handle.close()
            return False
        elif resp[0] == 0x47:
            print("Send Security Password (SP) first !")
            write_handle.close()
            return False

        efserr = False
        fh = FactoryHeader()
        if len(resp) > 0:
            write_handle.write(resp[0x10:-0x1])
            fefs.from_data(resp[0x8:0x10])
            fh.from_data(resp[0x10:0x10 + (39 * 4)])

        old = 0
        print_progress(0, 100, prefix="Progress:", suffix="Complete", bar_length=50)
        total = fh.block_size * fh.block_count * (fh.page_size // 0x200)

        # Real start
        for page in range(0, total):
            # EFS Cmd
            buf = pack("<BBBBBBHI", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_FACT_IMAGE_READ.value, 0x00,
                       fefs.stream_state, fefs.info_cluster_sent,
                       fefs.cluster_map_seqno, fefs.cluster_data_seqno)

            pos = int(page / total * 100)
            if pos > old:
                print_progress(pos, 100, prefix="Progress:", suffix="Page %d of %d" % (page, total), bar_length=50)
                old = pos

            resp = self.send(buf)
            if resp == 0:
                resp = self.send(buf)

            if resp == 0 or resp == -1:
                info = ("Page %08X !\n" % fefs.cluster_data_seqno)
                print(info)
                resp = self.send(buf)
                if resp == 0 or resp == -1:
                    print("Data Error occured, " + info)
            else:
                dlen = len(resp) - 0x11
                if dlen == 0x200 or dlen == 0x800:
                    if resp[0x0] == 0x4B:
                        write_handle.write(resp[0x10:0x10 + dlen])
                        fefs.from_data(resp[0x8:0x10])
                    else:
                        if (resp[0x0] == 0x13) and (resp[0x1] == 0x62) and (len(resp) > 0x200):
                            write_handle.write(resp[0x14:-4])
                            fefs.from_data(resp[0xc:0x14])
                            if fefs.stream_state == 0x0:
                                break
                        else:
                            print("EFS Read error : Wrong size recieved at page %X" % page)
                            efserr = True
                            break

        print_progress(100, 100, prefix="Progress:", suffix="Complete", bar_length=50)

        buf = bytearray()
        buf.append(0x4B)
        buf.append(efsmethod)
        buf.append(efs_cmds.EFS2_DIAG_FACT_IMAGE_END.value)  # end factory image
        buf.append(0x00)

        resp = self.send(buf)
        if len(resp) == 0:
            print("Phone does not respond. Maybe another software is blocking the port.")
            return False

        write_handle.close()
        if not efserr:
            print("Successfully read EFS.")
            return True
        else:
            print("Error on reading EFS.")
            return False

    def send_cmd(self, cmd):
        cmdtosend = unhexlify(cmd)
        reply = self.send(cmdtosend)
        if reply[0] != cmdtosend[0]:
            print(self.decode_status(reply))
        result = self.data_to_hex_ascii(reply)
        return result

    def efsdiagerror(self, errcode):
        if errcode == 0x40000001:
            print("Inconsistent state.")
        elif errcode == 0x40000002:
            print("Invalid seq no.")
        elif errcode == 0x40000003:
            print("Directory not open.")
        elif errcode == 0x40000004:
            print("Directory entry not found.")
        elif errcode == 0x40000005:
            print("Invalid path.")
        elif errcode == 0x40000006:
            print("Path too long")
        elif errcode == 0x40000007:
            print("Too many open directories.")
        elif errcode == 0x40000008:
            print("Invalid directory entry.")
        elif errcode == 0x40000009:
            print("Too many open files.")
        elif errcode == 0x4000000a:
            print("Unknown filetype")
        elif errcode == 0x4000000b:
            print("Not nand falsh")
        elif errcode == 0x4000000c:
            print("Unavailable info")
        else:
            return 0
        return -1

    def efs_closedir(self, efsmethod, dirp):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_CLOSEDIR.value, 0x00)  # list efs dir
        buf += pack("<I", dirp)
        resp = self.send(buf)
        diagerror = unpack("<I", resp[0x4:0x8])[0]
        return self.efsdiagerror(diagerror)

    def efs_opendir(self, efsmethod, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_OPENDIR.value, 0x00)  # open efs dir
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            dirp = unpack("<I", resp[0x4:0x8])[0]
            diagerror = unpack("<I", resp[0x8:0xC])[0]
            if self.efsdiagerror(diagerror) != 0:
                return -1
            return dirp

    def efslistdir(self, path):
        alternateefs = b"\x4B\x3E\x00\x00" + b"\x00" * 0x28
        standardefs = b"\x4B\x13\x00\x00" + b"\x00" * 0x28
        resp = self.send(alternateefs)
        if resp[0] == 0x4B:
            efsmethod = 0x3E
        else:
            resp = self.send(standardefs)
            if resp[0] == 0x4B:
                efsmethod = 0x13
            else:
                print("No known efs method detected for reading.")
                return

        dirp = self.efs_opendir(efsmethod, path)
        if dirp == -1:
            return

        info = ""
        for seqno in range(1, 0xFFFFFFFF):
            buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_READDIR.value, 0x00)  # list efs dir
            buf += pack("<II", dirp, seqno)
            resp = self.send(buf)
            if len(resp) > 0:
                [dirp, seqno, diag_errno, entry_type, mode, size, atime, mtime, ctime] = unpack("<Iiiiiiiii",
                                                                                                resp[4:4 + (9 * 4)])
                if entry_type == 1:
                    entry_name = resp[4 + (9 * 4):-1]
                    if len(entry_name) < 50:
                        entry_name += (50 - len(entry_name)) * b" "
                    info += f"{path}{entry_name.decode('utf-8')} mode:{hex(mode)}, size:{hex(size)}, atime:{hex(atime)}, mtime:{hex(mtime)}, ctime:{hex(ctime)}\n"
                elif entry_type == 0:
                    break
        if self.efs_closedir(efsmethod, dirp) != 0:
            print("Error on listing directory")
        return info

    def efs_open(self, efsmethod, oflag, mode, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_OPEN.value, 0x00)  # open efs dir
        buf += pack("<II", oflag, mode)
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            fdata = unpack("<i", resp[0x4:0x8])[0]
            diagerror = unpack("<I", resp[0x8:0xC])[0]
            if self.efsdiagerror(diagerror) != 0:
                return -1
            return fdata

    def efs_close(self, efsmethod, fdata):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_CLOSE.value, 0x00)  # list efs dir
        buf += pack("<i", fdata)
        resp = self.send(buf)
        diag_error = unpack("<I", resp[0x4:0x8])[0]
        return self.efsdiagerror(diag_error)

    def efs_stat(self, efsmethod, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_STAT.value, 0x00)  # open efs file
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            diag_error = unpack("<I", resp[0x4:0x8])[0]
            mode = unpack("<I", resp[0x8:0xC])[0]
            size = unpack("<I", resp[0xC:0x10])[0]
            nlink = unpack("<I", resp[0x10:0x14])[0]
            atime = unpack("<I", resp[0x14:0x18])[0]
            mtime = unpack("<I", resp[0x18:0x1C])[0]
            ctime = unpack("<I", resp[0x1C:0x20])[0]
            if self.efsdiagerror(diag_error) != 0:
                return -1
            return [mode, size, nlink, atime, mtime, ctime]

    def efs_fstat(self, efsmethod, fdata):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_FSTAT.value, 0x00)  # open efs file
        buf += pack("<I", fdata)
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            diag_error = unpack("<I", resp[0x4:0x8])[0]
            mode = unpack("<I", resp[0x8:0xC])[0]
            size = unpack("<I", resp[0xC:0x10])[0]
            nlink = unpack("<I", resp[0x10:0x14])[0]
            atime = unpack("<I", resp[0x14:0x18])[0]
            mtime = unpack("<I", resp[0x18:0x1C])[0]
            ctime = unpack("<I", resp[0x1C:0x20])[0]
            if self.efsdiagerror(diag_error) != 0:
                return -1
            return [mode, size, nlink, atime, mtime, ctime]

    def efs_lstat(self, efsmethod, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_LSTAT.value, 0x00)  # open efs file
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            diag_error = unpack("<I", resp[0x4:0x8])[0]
            mode = unpack("<I", resp[0x8:0xC])[0]
            atime = unpack("<I", resp[0xC:0x10])[0]
            mtime = unpack("<I", resp[0x10:0x14])[0]
            ctime = unpack("<I", resp[0x14:0x18])[0]
            if self.efsdiagerror(diag_error) != 0:
                return -1
            return [mode, atime, mtime, ctime]

    def efs_get(self, efsmethod, path, data_length, sequence_number):
        path_length = len(path) + 1
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_GET.value, 0x00)  # open efs file
        buf += pack("<IIH", data_length, path_length, sequence_number)
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            num_bytes = unpack("<I", resp[0x4:0x8])[0]
            diag_error = unpack("<I", resp[0x8:0xC])[0]
            seq_no = unpack("<H", resp[0xC:0xE])[0]
            data = resp[0xE:]
            if self.efsdiagerror(diag_error) != 0:
                return -1
            return [num_bytes, seq_no, data]

    def efs_write(self, efsmethod, fdata, offset, data):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_WRITE.value, 0x00)  # open efs file
        buf += pack("<II", fdata, offset)
        buf += data
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            fdata = unpack("<i", resp[0x4:0x8])[0]
            offset = unpack("<I", resp[0x8:0xC])[0]
            bytes_written = unpack("<I", resp[0xC:0x10])[0]
            diag_error = unpack("<I", resp[0x10:0x14])[0]
            if self.efsdiagerror(diag_error) != 0:
                return -1
            return [fdata, offset, bytes_written]

    def handle_error(self, resp):
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            diagerror = unpack("<I", resp[0x4:0x8])[0]
            if self.efsdiagerror(diagerror) != 0:
                return -1
            return 0

    def efs_rmdir(self, efsmethod, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_RMDIR.value, 0x00)  # open efs file
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        return self.handle_error(resp)

    def efs_unlink(self, efsmethod, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_UNLINK.value, 0x00)  # open efs file
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        return self.handle_error(resp)

    def efs_chown(self, efsmethod, uid_val, gid_val, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_CHOWN.value, 0x00)  # open efs file
        buf += pack("<ii", uid_val, gid_val)
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        return self.handle_error(resp)

    def efs_chmod(self, efsmethod, mode, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_CHMOD.value, 0x00)  # open efs file
        buf += pack("<H", mode)
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        return self.handle_error(resp)

    def efs_mkdir(self, efsmethod, mode, path):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_MKDIR.value, 0x00)  # open efs file
        buf += pack("<H", mode)
        buf += bytes(path, "utf-8") + b"\x00"
        resp = self.send(buf)
        return self.handle_error(resp)

    def efs_read(self, efsmethod, fdata, nbytes, offset):
        buf = pack("<BBBB", 0x4B, efsmethod, efs_cmds.EFS2_DIAG_WRITE.value, 0x00)  # open efs file
        buf += pack("<III", fdata, nbytes, offset)
        resp = self.send(buf)
        if resp[0] != diag_cmds.DIAG_BAD_SEC_MODE_F.value and resp[0] != diag_cmds.DIAG_BAD_LEN_F.value:
            fdata = unpack("<i", resp[0x4:0x8])[0]
            offset = unpack("<I", resp[0x8:0xC])[0]
            bytes_read = unpack("<I", resp[0xC:0x10])[0]
            diag_error = unpack("<I", resp[0x10:0x14])[0]
            data = resp[0x14:]
            if self.efsdiagerror(diag_error) != 0:
                return -1
            return [fdata, offset, bytes_read, data]

    def efsreadfile(self, srcpath, dstpath):
        alternateefs = b"\x4B\x3E\x00\x00" + b"\x00" * 0x28
        standardefs = b"\x4B\x13\x00\x00" + b"\x00" * 0x28
        resp = self.send(alternateefs)
        if resp[0] == 0x4B:
            efsmethod = 0x3E
        else:
            resp = self.send(standardefs)
            if resp[0] == 0x4B:
                efsmethod = 0x13
            else:
                logging.error("No known efs method detected for reading.")
                return 0

        fdata = self.efs_open(efsmethod, O_RDONLY, 0, srcpath)
        if fdata == -1:
            return 0
        mode, size, nlink, atime, mtime, ctime = self.efs_fstat(efsmethod, fdata)
        if size == 0:
            self.efs_close(efsmethod, fdata)
            return 0
        acr = (mode & O_ACCMODE)
        if acr == O_WRONLY:
            logging.error("File can only be written. Aborting.")
            self.efs_close(efsmethod, fdata)
            return 0

        num_bytes = 0
        offset = 0
        fname = srcpath[srcpath.rfind("/") + 1:]
        fname = os.path.join(dstpath, fname)
        with open(fname, "wb") as write_handle:
            dataleft = size
            while dataleft > 0:
                rsize = dataleft
                if rsize > FS_DIAG_MAX_READ_REQ:
                    rsize = FS_DIAG_MAX_READ_REQ
                finfo = self.efs_read(efsmethod, fdata, rsize, offset)
                if finfo == -1:
                    break
                fdata, offset, bytes_read, data = finfo
                write_handle.write(data)
                offset += rsize
                dataleft -= rsize
        self.efs_close(efsmethod, fdata)
        return num_bytes

    def efswritefile(self, srcpath, dstpath):
        alternateefs = b"\x4B\x3E\x00\x00" + b"\x00" * 0x28
        standardefs = b"\x4B\x13\x00\x00" + b"\x00" * 0x28
        resp = self.send(alternateefs)
        if resp[0] == 0x4B:
            efsmethod = 0x3E
        else:
            resp = self.send(standardefs)
            if resp[0] == 0x4B:
                efsmethod = 0x13
            else:
                logging.error("No known efs method detected for reading.")
                return 0
        with open(srcpath, "rb") as rf:
            fdata = self.efs_open(efsmethod, O_RDONLY, 0, srcpath)
            if fdata == -1:
                return 0
            mode, size, nlink, atime, mtime, ctime = self.efs_fstat(efsmethod, fdata)
            if size == 0:
                self.efs_close(efsmethod, fdata)
                return 0
            """
            acr=(mode & O_ACCMODE)
            if acr==O_RDONLY:
                print("File can only be read. Aborting.")
                self.efs_close(efsmethod, fdata)
                return
            """
            num_bytes = 0
            offset = 0
            size = os.fstat(srcpath).st_size
            dataleft = size
            while dataleft > 0:
                rsize = dataleft
                if rsize > FS_DIAG_MAX_READ_REQ:
                    rsize = FS_DIAG_MAX_READ_REQ
                data = rf.read(rsize)
                finfo = self.efs_write(efsmethod, fdata, offset, data)
                if finfo == -1:
                    break
                fdata, offset, bytes_written = finfo
                offset += rsize
                dataleft -= rsize
            self.efs_close(efsmethod, fdata)
        return num_bytes


class DiagTools(metaclass=LogBase):
    def run(self, args):
        self.interface = -1
        self.vid = None
        self.pid = None
        try:
            self.serial = args.serial
        except:
            self.serial = False
        try:
            self.portname = args.port_name
        except:
            self.portname = ""

        if self.portname is not None and self.portname != "":
            self.serial = True
        try:
            self.vid = int(args.vid, 16)
        except:
            pass
        try:
            self.pid = int(args.pid, 16)
        except:
            pass
        try:
            self.interface = int(args.interface, 16)
        except:
            pass

        try:
            self.debugmode = args.debugmode
        except:
            self.debugmode = False

        if self.vid is not None:
            self.vid = int(args.vid, 16)
        if self.pid is not None:
            self.pid = int(args.pid, 16)

        logfilename = "diag.txt"
        if self.debugmode:
            if os.path.exists(logfilename):
                os.remove(logfilename)
            fh = logging.FileHandler(logfilename)
            self._logger.addHandler(fh)
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

        connected = False
        diag = None
        if self.vid is None or self.pid is None:
            diag = QualcommDiagClient(loglevel=self._logger.level, port_config=default_diag_vid_pid)
            if self.serial:
                diag.port_name = self.portname
            connected = diag.connect(self.serial)
        else:
            diag = QualcommDiagClient(loglevel=self._logger.level, port_config=[[self.vid, self.pid, self.interface]])
            if self.serial:
                diag.port_name = self.portname
            connected = diag.connect(self.serial)

        if connected:
            cmd = args.cmd
            if cmd == "sp":
                diag.send_sp(args.spval)
            elif cmd == "spc":
                diag.send_spc(args.spcval)
            elif cmd == "cmd":
                if args.cmdval == "":
                    print("cmd needed as hex string, example: 00")
                else:
                    print(diag.send_cmd(args.cmdval))
            elif cmd == "info":
                print(diag.cmd_info())
            elif cmd == "download":
                diag.enter_downloadmode()
            elif cmd == "sahara":
                diag.enter_saharamode()
            elif cmd == "crash":
                diag.enforce_crash()
            elif cmd == "efslistdir":
                print(diag.efslistdir(args.path))
            elif cmd == "efsreadfile":
                if args.src == "" or args.dst == "":
                    print("Usage: -efsreadfile -src srcfile -dst dstfile")
                    sys.exit()
                print(diag.efsreadfile(args.src, args.dst))
            elif cmd == "nvread":
                if "0x" in args.NVitem:
                    nvitem = int(args.NVitem, 16)
                else:
                    nvitem = int(args.NVitem)
                diag.print_nvitem(nvitem)
            elif cmd == "nvreadsub":
                if args.NVitem is None or args.nvindex is None:
                    print("Usage: nvreadsub [nvitem] [nvindex]")
                    exit(1)
                nv = args.nvreadsub.split(",")
                if "0x" in args.NVitem:
                    nvitem = int(args.NVitem, 16)
                else:
                    nvitem = int(args.NVitem)
                if "0x" in nv[1]:
                    nvindex = int(args.nvindex, 16)
                else:
                    nvindex = int(args.nvindex)
                diag.print_sub_nvitem(nvitem, nvindex)
            elif cmd == "nvwrite":
                if args.data is None:
                    print("NvWrite requires data to write")
                    sys.exit()
                if "0x" in args.NVitem:
                    nvitem = int(args.NVitem, 16)
                else:
                    nvitem = int(args.NVitem)
                data = unhexlify(args.data)
                diag.write_nvitem(nvitem, data)
            elif cmd == "nvwritesub":
                if args.NVitem is None or args.nvindex is None or args.data is None:
                    print("NvWriteSub requires item, index and data to write")
                    sys.exit()
                if "0x" in args.NVitem:
                    nvitem = int(args.NVitem, 16)
                else:
                    nvitem = int(args.NVitem)
                if "0x" in args.nvindex:
                    nvindex = int(args.nvindex, 16)
                else:
                    nvindex = int(args.nvindex)
                data = unhexlify(args.data)
                diag.write_nvitemsub(nvitem, nvindex, data)
            elif cmd == "nvbackup":
                diag.backup_nvitems(args.filename, "error.log")
            elif cmd == "writeimei":
                diag.write_imei(args.imei)
            elif cmd == "efsread":
                diag.efsread(args.filename)
            else:
                print("A command is required. Use -cmd \"data\" for sending requests.")
                print()
                print("Valid commands are:")
                print("-------------------")
                print("info cmd sp spc nvread nvreadsub" +
                      " nvwrite writeimei nvwritesub nvbackup efsread efsreadfile" +
                      " efslistdir download sahara crash")
                print()
            diag.disconnect()
            sys.exit()
        else:
            print("No diag device detected. Use -pid and -vid options. See -h for help.")
            diag.disconnect()
            sys.exit()


def main():
    info = "Qualcomm Diag Client (c) B.Kerler 2019-2021."
    parser = argparse.ArgumentParser(description=info)
    print("\n" + info + "\n---------------------------------------\n")
    subparser = parser.add_subparsers(dest="cmd", help="Valid commands are:\ninfo cmd sp spc nvread nvreadsub" +
                                                       " nvwrite writeimei nvwritesub nvbackup efsread efsreadfile\n" +
                                                       " efslistdir download sahara crash")

    parser_info = subparser.add_parser("info", help="[Option] Get diag info")
    parser_info.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_info.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_info.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                             default="0")
    parser_info.add_argument("-port_name", metavar="<port_name>",
                             help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_info.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_info.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_cmd = subparser.add_parser("cmd", help="Send command")
    parser_cmd.add_argument("cmdval", help="cmd to send (hexstring), default: 00",
                            default="", const="00", nargs="?")
    parser_cmd.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_cmd.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_cmd.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                            default="0")
    parser_cmd.add_argument("-port_name", metavar="<port_name>",
                            help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_cmd.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_cmd.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_sp = subparser.add_parser("sp", help="Send Security password")
    parser_sp.add_argument("spval", help="Security password to send, default: FFFFFFFFFFFFFFFE",
                           default="FFFFFFFFFFFFFFFE", nargs="?")
    parser_sp.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_sp.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_sp.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                           default="0")
    parser_sp.add_argument("-port_name", metavar="<port_name>",
                           help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_sp.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_sp.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_spc = subparser.add_parser("spc", help="Send Security Code")
    parser_spc.add_argument("spcval", help="Security code to send, default: 303030303030",
                            default="303030303030", nargs="?")
    parser_spc.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_spc.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_spc.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                            default="0")
    parser_spc.add_argument("-port_name", metavar="<port_name>",
                            help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_spc.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_spc.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_nvread = subparser.add_parser("nvread", help="Read nvitem")
    parser_nvread.add_argument("nvitem", help="[Option] NVItem to read", default="")
    parser_nvread.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_nvread.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_nvread.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                               default="0")
    parser_nvread.add_argument("-port_name", metavar="<port_name>",
                               help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_nvread.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_nvread.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_nvreadsub = subparser.add_parser("nvreadsub", help="Read nvitem using subsystem")
    parser_nvreadsub.add_argument("nvitem", help="[Option] NVItem to read", default="")
    parser_nvreadsub.add_argument("nvindex", help="[Option] Index to read", default="")
    parser_nvreadsub.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_nvreadsub.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_nvreadsub.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                  default="0")
    parser_nvreadsub.add_argument("-port_name", metavar="<port_name>",
                                  help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_nvreadsub.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_nvreadsub.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_nvwrite = subparser.add_parser("nvwrite", help="Write nvitem")
    parser_nvwrite.add_argument("nvitem", help="[Option] NVItem to write", default="")
    parser_nvwrite.add_argument("data", help="[Option] Data to write", default="")
    parser_nvwrite.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_nvwrite.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_nvwrite.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                default="0")
    parser_nvwrite.add_argument("-port_name", metavar="<port_name>",
                                help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_nvwrite.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_nvwrite.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_nvwritesub = subparser.add_parser("nvwritesub", help="Write nvitem using subsystem")
    parser_nvwritesub.add_argument("nvitem", help="[Option] NVItem to read", default="")
    parser_nvwritesub.add_argument("nvindex", help="[Option] Index to read", default="")
    parser_nvwritesub.add_argument("data", help="[Option] Data to write", default="")
    parser_nvwritesub.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_nvwritesub.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_nvwritesub.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                   default="0")
    parser_nvwritesub.add_argument("-port_name", metavar="<port_name>",
                                   help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_nvwritesub.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_nvwritesub.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_writeimei = subparser.add_parser("writeimei", help="Write imei")
    parser_writeimei.add_argument("imei", metavar="<imei1,imei2,...>", help="[Option] IMEI to write", default="")
    parser_writeimei.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_writeimei.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_writeimei.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                  default="0")
    parser_writeimei.add_argument("-port_name", metavar="<port_name>",
                                  help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_writeimei.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_writeimei.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_nvbackup = subparser.add_parser("nvbackup", help="Make nvitem backup as json")
    parser_nvbackup.add_argument("filename", help="[Option] Filename to write to", default="")
    parser_nvbackup.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_nvbackup.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_nvbackup.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                 default="0")
    parser_nvbackup.add_argument("-port_name", metavar="<port_name>",
                                 help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_nvbackup.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_nvbackup.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_efsread = subparser.add_parser("efsread", help="Read efs")
    parser_efsread.add_argument("filename", help="[Option] Filename to write to", default="")
    parser_efsread.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_efsread.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_efsread.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                default="0")
    parser_efsread.add_argument("-port_name", metavar="<port_name>",
                                help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_efsread.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_efsread.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_efsreadfile = subparser.add_parser("efsreadfile", help="Read efs file")
    parser_efsreadfile.add_argument("src", help="[Option] Source filename", default="")
    parser_efsreadfile.add_argument("dst", help="[Option] Destination filename", default="")
    parser_efsreadfile.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_efsreadfile.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_efsreadfile.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                    default="0")
    parser_efsreadfile.add_argument("-port_name", metavar="<port_name>",
                                    help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_efsreadfile.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_efsreadfile.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_efslistdir = subparser.add_parser("efslistdir", help="List efs directory")
    parser_efslistdir.add_argument("path", help="[Option] Path to list", default="")
    parser_efslistdir.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_efslistdir.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_efslistdir.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                   default="0")
    parser_efslistdir.add_argument("-port_name", metavar="<port_name>",
                                   help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_efslistdir.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_efslistdir.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_download = subparser.add_parser("download", help="[Option] Switch to sahara mode")
    parser_download.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_download.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_download.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                                 default="0")
    parser_download.add_argument("-port_name", metavar="<port_name>",
                                 help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_download.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_download.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_sahara = subparser.add_parser("sahara", help="[Option] Switch to sahara mode")
    parser_sahara.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_sahara.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_sahara.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                               default="0")
    parser_sahara.add_argument("-port_name", metavar="<port_name>",
                               help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_sahara.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_sahara.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    parser_crash = subparser.add_parser("crash", help="[Option] Enforce crash")
    parser_crash.add_argument("-vid", metavar="<vid>", help="[Option] Specify vid", default="")
    parser_crash.add_argument("-pid", metavar="<pid>", help="[Option] Specify pid", default="")
    parser_crash.add_argument("-interface", metavar="<pid>", help="[Option] Specify interface number, default=0)",
                              default="0")
    parser_crash.add_argument("-port_name", metavar="<port_name>",
                              help="[Option] Specify serial port (\"/dev/ttyUSB0\",\"COM1\")")
    parser_crash.add_argument("-serial", help="[Option] Use serial port (autodetect)", action="store_true")
    parser_crash.add_argument("-debugmode", help="[Option] Enable verbose logging", action="store_true")

    args = parser.parse_args()
    dg = DiagTools()
    dg.run(args)


if __name__ == "__main__":
    main()
