#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!
#
# Modified by: Kai (dev-kai0602) 2025 under GPLv3 license
# Modifications:
# - Added color-formatted logging system (ColorFormatter class)
# - Optimized serial port communication logic for EDL mode
# - Fixed EFS partition readback compatibility issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
logging 模块的扩展模块，适用于该项目。
"""
import logging, logging.config, copy, os, colorama

def logsetup(self, logger, loglevel):
    """配置日志级别、日志文件，并绑定日志方法到实例.

    Args:
        self: 调用该方法的类实例（通常是LogBase元类创建的类实例）
        logger: 待配置的日志器对象
        loglevel: 日志级别（logging.DEBUG / logging.INFO）

    Returns:
        配置完成的日志器对象

    Side effects:
        1. 为实例绑定info/debug/error/warning日志方法
        2. 若为DEBUG级别：
           - 清理并创建logs/log.txt日志文件
           - 为日志器添加文件处理器
        3. 设置实例的log_level属性
    """
    self.info = logger.info
    self.debug = logger.debug
    self.error = logger.error
    self.warning = logger.warning
    
    if loglevel == logging.DEBUG:
        log_file_name = os.path.join("logs", "log.txt")
        if os.path.exists(log_file_name):
            try:
                os.remove(log_file_name)
            except OSError:
                pass
        file_handler = logging.FileHandler(log_file_name, encoding="utf-8")
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    self.log_level = loglevel
    
    return logger


class ColorFormatter(logging.Formatter):
    """自定义日志格式化器，为不同级别日志添加终端颜色.

    特性:
    - 深拷贝日志记录对象，避免修改原记录影响其他处理器
    - 非root日志器添加[LIB]: 前缀标识
    - 按级别着色：ERROR(红) / DEBUG(浅紫) / WARNING(黄)
    """
    LOG_COLORS = {
        logging.ERROR: colorama.Fore.RED,
        logging.DEBUG: colorama.Fore.LIGHTMAGENTA_EX,
        logging.WARNING: colorama.Fore.YELLOW,
    }
    
    def format(self, record, *args, **kwargs):
        """格式化日志记录，添加颜色和前缀.

        Args:
            record: 日志记录对象（包含日志级别、消息、名称等信息）
            *args: 兼容父类方法的可变参数
            **kwargs: 兼容父类方法的关键字参数

        Returns:
            带颜色格式化后的日志字符串
        """
        # if the corresponding logger has children, they may receive modified
        # record, so we want to keep it intact
        new_record = copy.copy(record)
        if new_record.levelno in self.LOG_COLORS:
            pad = ''
            if new_record.name != "root":
                print(new_record.name)
                pad = "[LIB]: "
            # we want levelname to be in different color, so let"s modify it
            new_record.msg = "{pad}{color_begin}{msg}{color_end}".format(
                pad=pad,
                msg=new_record.msg,
                color_begin=self.LOG_COLORS[new_record.levelno],
                color_end=colorama.Style.RESET_ALL,
            )
        # now we can let standart formatting take care of the rest
        # return super(ColorFormatter, self).format(new_record, *args, **kwargs) # 旧方法
        return super().format(new_record, *args, **kwargs)
