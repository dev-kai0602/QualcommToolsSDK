#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2024 under GPLv3 license
# If you use my code, make sure you refer to my name
#
# !!!!! If you use this code in commercial products, your product is automatically
# GPLv3 and has to be open sourced under GPLv3 as well. !!!!!

# 默认USB设备标识列表（基础版，均无特殊配置参数）
# 格式：[厂商ID(VID), 产品ID(PID), 配置参数(-1表示无)]
default_ids = [
    [0x05c6, 0x9008, -1],  # 高通（Qualcomm）- 紧急下载模式（EDL）设备
    [0x0fce, 0x9dde, -1],  # 索尼（SONY）- EDL模式设备
    [0x0fce, 0xade5, -1],  # 索尼（SONY）- EDL模式设备
    [0x0fce, 0xaded, -1],  # 索尼（SONY）- EDL模式设备
    [0x05c6, 0x900e, -1],  # 高通（Qualcomm）- EDL模式设备
    [0x05c6, 0x9025, -1],  # 高通（Qualcomm）- EDL模式设备
    [0x1199, 0x9062, -1],  # 塞拉无线（Sierra Wireless）- 调制解调器设备
    [0x1199, 0x9070, -1],  # 塞拉无线（Sierra Wireless）- 调制解调器设备
    [0x1199, 0x9090, -1],  # 塞拉无线（Sierra Wireless）- 调制解调器设备
    [0x0846, 0x68e0, -1],  # 网件（Netgear）- 无线模块/调制解调器设备
    [0x19d2, 0x0076, -1]   # 中兴（ZTE）- 下载模式设备
]

# 诊断模式USB设备标识列表（进阶版，含细分配置参数）
# 格式：[厂商ID(VID), 产品ID(PID), 配置参数(接口序号/通信模式/配置集编号)]
default_diag_vid_pid = [
    [0x2c7c, 0x0125, -1],  # 移远（Quectel）- EC25系列物联网模块（无特殊配置）
    [0x1199, 0x9071, -1],  # 塞拉无线（Sierra Wireless）- 调制解调器设备（无特殊配置）
    [0x1199, 0x9091, -1],  # 塞拉无线（Sierra Wireless）- 调制解调器设备（无特殊配置）
    [0x0846, 0x68e2,  2],  # 网件（Netgear）- 无线模块（配置参数2：USB接口序号/MBIM模式）
    [0x05C6, 0x9008, -1],  # 高通（Qualcomm）- 紧急下载模式（EDL）设备（无特殊配置）
    [0x0fce, 0x9dde, -1],  # 索尼（SONY）- EDL模式设备（无特殊配置）
    [0x0fce, 0xade5, -1],  # 索尼（SONY）- EDL模式设备（无特殊配置）
    [0x0fce, 0xaded, -1],  # 索尼（SONY）- EDL模式设备（无特殊配置）
    [0x05C6, 0x676C, 0],   # 高通（Qualcomm）- 手持设备/手机（配置参数0：默认通信模式）
    [0x05c6, 0x901d, 0],   # 高通（Qualcomm）- Android设备（配置参数0：diag+adb模式，需执行setprop指令）
    [0x19d2, 0x0016, -1],  # 中兴（ZTE）- 诊断（Diag）模式设备（无特殊配置）
    [0x19d2, 0x0076, -1],  # 中兴（ZTE）- 下载模式设备（无特殊配置）
    [0x19d2, 0x0500, -1],  # 中兴（ZTE）- Android设备（无特殊配置）
    [0x19d2, 0x1404, 2],  # 中兴（ZTE）- ADB+调制解调器模式（配置参数2：USB接口序号）
    [0x12d1, 0x1506, -1],  # 华为（Huawei）- 调制解调器/无线模块（无特殊配置）
    [0x413c, 0x81d7, 5],  # 泰利特（Telit）- LN940/T77W968工业模块（配置参数5：QMI通信模式/接口序号）
    [0x1bc7, 0x1040, 0],  # 泰利特（Telit）- LM960A18模块（配置参数0：USBCFG 1，QMI通信模式）
    [0x1bc7, 0x1041, 0],  # 泰利特（Telit）- LM960A18模块（配置参数0：USBCFG 2，MBIM通信模式）
    [0x1bc7, 0x1201, 0],  # 泰利特（Telit）- LE910C4-NF工业模块（配置参数0：默认模式）
    [0x05c6, 0x9091, 0],   # 高通（Qualcomm）- 调制解调器/手机（配置参数0：默认通信模式）
    [0x05c6, 0x9092, 0],   # 高通（Qualcomm）- 调制解调器/手机（配置参数0：默认通信模式）
    [0x1e0e, 0x9001, -1],  # 芯讯通（Simcom）- SIM7600G无线通信模块（无特殊配置）
    [0x2c7c, 0x0700, -1]   # 移远（Quectel）- BG95-M3物联网模块（无特殊配置）
]
