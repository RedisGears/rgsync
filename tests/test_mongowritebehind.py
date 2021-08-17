import pytest
import tox
import toml
from RLTest import Env
from pymongo import MongoClient
import os


@pytest.mark.mongo
class TestMongo:

    @classmethod
    def teardown_class(cls):
        cls.dbconn.drop_database(cls.DBNAME)

    def setup_class(cls):
        cls.env = Env()

        # build the path to the built rgsync, as it is in the docker
        ll = toml.load("pyproject.toml")
        version = ll['tool']['poetry']['version']
        rgsync_pkg =  "rgsync-{}-py3-none-any.whl".format(version)

        # determine whether or not we're running in a docker
        in_docker = False
        if os.path.isfile("/.dockerenv") or \
            os.environ.get("IN_DOCKER", None) is not None:
            in_docker = True

        # install package
        if os.path.join(os.getcwd(), "dist", rgsync_pkg):
            if in_docker:
                pkg = os.path.join("/build", "dist", rgsync_pkg)
            else:
                pkg = os.path.join(os.getcwd(), "dist", rgsync_pkg)
        else:
            pkg = "rgsync"

        # connection info
        r = tox.config.parseconfig(open("tox.ini").read())
        docker = r._docker_container_configs["mongo"]["environment"]
        dbuser = docker["MONGO_INITDB_ROOT_USERNAME"]
        dbpasswd = docker["MONGO_INITDB_ROOT_PASSWORD"]
        db = docker["MONGO_DB"]
        cls.DBNAME = db

        con = "mongodb://{user}:{password}@172.17.0.1:27017/{db}?authSource=admin".format(
            user=dbuser,
            password=dbpasswd,
            db=db,
        )

        script = """
from rgsync import RGWriteBehind, RGWriteThrough
from rgsync.Connectors import MongoConnector, MongoConnection

connection = MongoConnection('%s', '%s', '172.17.0.1:27017/%s')

personsConnector = MongoConnector(connection, 'persons', 'person_id')

personsMappings = {
    'first_name':'first',
    'last_name':'last',
    'age':'age'
}

RGWriteBehind(GB,  keysPrefix='person', mappings=personsMappings, connector=personsConnector, name='PersonsWriteBehind',  version='99.99.99')

RGWriteThrough(GB, keysPrefix='__',     mappings=personsMappings, connector=personsConnector, name='PersonsWriteThrough', version='99.99.99')
""" % (dbuser, dbpasswd, db)
        cls.env.cmd('RG.PYEXECUTE', script, 'REQUIREMENTS', pkg, 'pymongo')

        e = MongoClient(con)

        # tables are only created upon data use - so this is our equivalent
        # for mongo
        assert 'version' in e.server_info().keys()
        cls.dbconn = e

    def testSimpleWriteBehind(self):
        print('ehllo world!')