import MySQLdb

DBNAME = "joetraffic"
DBHOST = "localhost"
DBUSER = "root"
DBPASSWD = "fjdk111"

class DB:
    def __init__(self, db):
        self._db = db
        self._cursor = db.cursor()
    def execute(self, cmd):
        self._cursor.execute(cmd)
        return self._cursor.fetchall()

_db = DB(MySQLdb.connect(db=DBNAME, host=DBHOST, user=DBUSER, passwd=DBPASSWD))

def escape(val):
    return MySQLdb.escape_string(val)

def getDB():
    return _db
