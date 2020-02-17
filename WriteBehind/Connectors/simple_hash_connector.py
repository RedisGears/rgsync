from redisgears import executeCommand as execute

SIMPLE_HASH_BACKEND_PK = 'SimpleHashBackendPK'
SIMPLE_HASH_BACKEND_TABLE = 'SimpleHashBackendTable'

class SimpleHashConnector():
    def __init__(self, newPefix):
        self.newPefix = newPefix

    def TableName(self):
        return SIMPLE_HASH_BACKEND_TABLE

    def PrimaryKey(self):
        return SIMPLE_HASH_BACKEND_PK

    def WriteData(self, data):
        for e in data:
            pk = e.pop(SIMPLE_HASH_BACKEND_PK)
            streamId = e.pop('streamId')
            newKey = '%s:%s' % (self.newPefix, pk)
            d = [[k, v] for k,v in e.items() if not k.startswith('_')]
            res = execute('hset', newKey, *sum(d, []))
            if 'ERR' in str(res):
                raise Exception(res)
