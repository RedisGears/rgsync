from redisgears import getMyHashTag as hashtag
from redisgears import log

NAME = 'WRITE_BEHIND'
ORIGINAL_KEY = '_original_key'
UUID_KEY = '_uuid'
OP_KEY = '#'

OPERATION_DEL_REPLICATE = '~'
OPERATION_DEL_NOREPLICATE = '-'
OPERATION_UPDATE_REPLICATE = '='
OPERATION_UPDATE_NOREPLICATE = '+'
OPERATIONS = [OPERATION_DEL_REPLICATE, OPERATION_DEL_NOREPLICATE, OPERATION_UPDATE_REPLICATE, OPERATION_UPDATE_NOREPLICATE]
defaultOperation = OPERATION_UPDATE_REPLICATE

def WriteBehindLog(msg, prefix='%s - ' % NAME, logLevel='notice'):
    msg = prefix + msg
    log(msg, level=logLevel)

def WriteBehindDebug(msg):
    WriteBehindLog(msg, logLevel='debug')

def CreateGetStreamNameCallback(uid):
    def GetStreamName(tableName):
        return '_%s-stream-%s-{%s}' % (tableName, uid, hashtag())
    return GetStreamName

def CompareIds(id1, id2):
    id1_time, id1_num = [int(a) for a in id1.split('-')]
    id2_time, id2_num = [int(a) for a in id2.split('-')]
    if(id1_time > id2_time):
        return 1
    if(id1_time < id2_time):
        return -1

    if(id1_num > id2_num):
        return 1
    if(id1_num < id2_num):
        return -1

    return 0

