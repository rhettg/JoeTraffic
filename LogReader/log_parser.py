import sys, logging

log = logging.getLogger('log_parser')

if __name__ == '__main__':
    sys.path.append('..')

import re, datetime, string
import db_interface

TABLENAME = "raw_web"
MAXLINESIZE = 1024

MONTHS = {'Jan': 1,
        'Feb': 2,
        'Mar': 3,
        'Apr': 4,
        'May': 5,
        'Jun': 6,
        'Jul': 7,
        'Aug': 8,
        'Sep': 9,
        'Oct': 10,
        'Nov': 11,
        'Dec': 12}

URI_FILTERS = [
                #re.compile("[\S]* [\S]*(\.swf|\.css|\.js|\.jpg|\.gif|\.mov)([?|&][\S]*)? [\S]*")
              ]

IP_FILTERS = []



REG_WEB = re.compile("(?P<ip>[\d\.]*) - - \[(?P<timestamp>.*)\] (?P<domain>.*) \"(?P<uri>.*)\" (?P<size>[\d]*) (?P<response>.*) \"(?P<referrer>.*)\" \"(.*)\" \"(?P<ua>.*)\" \"(?P<cookie>.*)\"")
#REG_WEB = re.compile("(?P<ip>[\d\.]*) - - \[(?P<timestamp>.*)\] \"(?P<uri>.*)\" (?P<response>[\S]*) (?P<size>[\S]*) (?P<domain>.*) \"(?P<referrer>.*)\" \"(?P<ua>.*)\" \"(?P<cookie>.*)\".*")
REG_DATE = re.compile("(?P<day>[\d]+)\/(?P<month>\S+)\/(?P<year>\d+)\:(?P<hour>\d+)\:(?P<minute>\d+)\:(?P<second>\d+) (?P<offset>[+|-]\d+)")

class EndOfLogException(Exception): pass

class InvalidLogException(Exception): pass

def is_filtered(ip, uri, referrer):
    for reg in URI_FILTERS:
        if reg.search(uri) != None:
            return 1
    for reg in IP_FILTERS:
        if reg.search(ip) != None:
            return 1

def read_log(file, db, num_lines):
    """Function to parse lines from a log file and insert them into a database
       table.
       file: File object of the log file
       db: db_interface object to use
       num_lines: Number of lines to read
       
       This function may throw exceptions:
           EndOfLogException: Reached EOF
           InvalidLogException: Log file is of unknown format
        
        Return size, in bytes, read.  """

    found_valid = False
    line_count = 0
    bytes_read = 0
    line = file.readline(MAXLINESIZE)
    while line != "" and line_count < num_lines:
        bytes_read += len(line)
        line = string.strip(line)

        mtch = REG_WEB.search(line)
        if mtch is None:
            log.warning("Failed to Match: %s" % line)
        else:
            found_valid = True
            if not is_filtered(mtch.group("ip"), mtch.group("uri"),
                           mtch.group("referrer")):

                time_mtch = REG_DATE.search(mtch.group("timestamp"))
                timestamp = datetime.datetime(int(time_mtch.group("year")),
                                              MONTHS[time_mtch.group("month")],
                                              int(time_mtch.group("day")),
                                              int(time_mtch.group("hour")),
                                              int(time_mtch.group("minute")),
                                              int(time_mtch.group("second")))

                cmd = "INSERT INTO %s (ip, time, domain, uri, referrer, ua, cookie) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')" % \
                                   (TABLENAME,
                                    mtch.group("ip"),
                                    timestamp.isoformat(' '),
                                    mtch.group("domain"),
                                    db_interface.escape(mtch.group("uri")),
                                    db_interface.escape(mtch.group("referrer")),
                                    db_interface.escape(mtch.group("ua")),
                                    db_interface.escape(mtch.group("cookie")))
                db.execute(cmd)
                #log.debug("Inserted hit into db: %s %s %s" % 
                          #(mtch.group("ip"),
                          #timestamp.isoformat(' '),
                          #mtch.group("uri")))
            else:
                log.debug("Filtered Hit")


        line_count += 1
        line = file.readline(MAXLINESIZE)

    if line == "":
        raise EndOfLogException("Finished reading logfile")

    elif not found_valid:
        raise InvalidLogException("Failed to find a matching line")

    log.debug("Finished reading %d lines (%d bytes), returning %d" % 
              (num_lines, bytes_read, line_count))
    return bytes_read           

    
if __name__ == '__main__':
    log_hndler = logging.StreamHandler()
    log_fmt = logging.Formatter(logging.BASIC_FORMAT)
    log_hndler.setFormatter(log_fmt)
    log.addHandler(log_hndler)
    log.setLevel(logging.DEBUG)

    if len(sys.argv) < 2:
        log.error("Log file not specified")
        sys.exit(1)

    logfile = sys.argv[1]
    log.info("Reading logfile %s" % logfile)
    hndl = open(logfile, 'r')
    db = db_interface.getDB()
    stop = False
    while not stop:
        try:
            bytes = read_log(hndl, db, 2)
            log.debug("Finished reading %d bytes" % bytes)
        except EndOfLogException, e:
            log.info("Finished reading log")
            stop = True

