from redisgears import getMyHashTag as hashtag
from redisgears import log as Log

NAME = 'WRITE_BEHIND'
ORIGINAL_KEY = '_original_key'
UUID_KEY = '_uuid'

def WriteBehindLog(msg, prefix='%s - ' % NAME, logLevel='notice'):
    msg = prefix + msg
    Log(logLevel, msg)

def WriteBehindDebug(msg):
    WriteBehindLog(msg, logLevel='debug')

def GetStreamName(tableName):
    return '_%s-stream-{%s}' % (tableName, hashtag())