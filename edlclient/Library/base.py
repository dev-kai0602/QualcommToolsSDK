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
扩展Python标准logging模块的彩色日志工具集.

核心功能:
- 支持DEBUG/INFO级别日志配置，DEBUG级会生成日志文件
- 终端日志按级别着色（ERROR:红 / DEBUG:浅紫 / WARNING:黄）
- 基于元类自动初始化日志器，简化日志使用流程
"""

import logging, logging.config

from edlclient.Tools.loggingTools import ColorFormatter, logsetup

class LogBase(type):
    debuglevel = logging.root.level

    def __init__(cls, *args):
        super().__init__(*args)
        logger_name = ".".join([c.__name__ for c in cls.mro()[-2::-1]])
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "root": {
                    "()": ColorFormatter,
                    "format": "%(name)s - %(message)s",
                }
            },
            "handlers": {
                "root": {
                    # "level": cls._logger.level,
                    "formatter": "root",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                }
            },
            "loggers": {
                "": {
                    "handlers": ["root"],
                    # "level": cls.debuglevel,
                    "propagate": False
                }
            },
        }
        logging.config.dictConfig(log_config)
        logger = logging.getLogger(logger_name)

        setattr(cls, '_logger', logger)
        setattr(cls, '_debuglevel', cls.debuglevel)
        cls.logsetup = logsetup
