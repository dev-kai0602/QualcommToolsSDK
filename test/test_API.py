# 系统: Ubuntnu 25.10
import sys

from edlclient.Library import api

args = api.default_edl_args.copy()
args['--debugmode'] = True
args['--genxml'] = True

phone = api.EDL_API(args, enabled_print=True, enabled_log=True)
if phone.init():
    print('初始化成功')
else:
    print('初始化失败')
    sys.exit(1)
