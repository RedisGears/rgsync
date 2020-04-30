from redisgears import getMyHashTag as hashtag
from redisgears import log
import uuid

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

UUID = str(uuid.uuid4())

def WriteBehindLog(msg, prefix='%s - ' % NAME, logLevel='notice'):
    msg = prefix + msg
    log(msg, level=logLevel)

def WriteBehindDebug(msg):
    WriteBehindLog(msg, logLevel='debug')

def GetStreamName(tableName):
    global UUID
    return '_%s-stream-%s-{%s}' % (tableName, UUID, hashtag())

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

