
# JoeTraffic - Web-Log Analysis Application utilizing the JoeAgent Framework.
# Copyright (C) 2004 Rhett Garber

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import MySQLdb

DBNAME = "joetraffic"
DBHOST = "localhost"
DBUSER = "root"
DBPASSWD = "passwd"

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
