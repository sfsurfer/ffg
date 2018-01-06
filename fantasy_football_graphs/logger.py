import datetime

class Logger:
  TRACE="TRACE"
  DEBUG="DEBUG"
  INFO="INFO"
  WARN="WARNING"
  WARNING="WARNING"
  ERROR="ERROR"
  TAG=""
  DEFAULT_LEVEL="INFO" # TODO: should move log level to config file
  LEVELS = [TRACE,DEBUG,INFO,WARNING,ERROR]

  # TODO: Allow for log to file
  def __init___(self, lvl=DEFAULT_LEVEL):
    print "INITIALIZING LOGGER"
    self.log_level = lvl

  def set_level(self, lvl):
    self.log_level = lvl

  def log(self, msg, lvl):
    if self.LEVELS.index(lvl) >= self.LEVELS.index(self.log_level):
      print(self.TAG + str(datetime.datetime.now()) + lvl + msg)
