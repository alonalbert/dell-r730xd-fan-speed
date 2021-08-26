#!/usr/bin/python
#
import argparse
import logging
import sqlite3
import subprocess
import sys
import time
from collections import namedtuple
from logging.handlers import RotatingFileHandler

FanSpeed = namedtuple("TempFanSpeed", [
  "cpuTemp",
  "fanSpeedPercent",
])

FAN_SPEED_MAP = {
  48: 50,
  47: 45,
  46: 40,
  45: 35,
  44: 30,
  43: 25,
  42: 20,
}

MAX_EXHAUST_TEMP = 35.0
MAX_CPU_TEMP = sorted(FAN_SPEED_MAP.keys())[len(FAN_SPEED_MAP) - 1]

LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

logger = None
db = None

Sensors = namedtuple("Sensors", [
  "temp_inlet",
  "temp_exhaust",
  "temp_cpu1",
  "temp_cpu2",
  "rpm_fan1",
  "rpm_fan2",
  "rpm_fan3",
  "rpm_fan4",
  "rpm_fan5",
  "rpm_fan6",
])


def main():
  log(logging.INFO, "Reading sensors:")
  sensors = read_sensors()
  log_sensors(sensors)

  fan_control = sensors.rpm_fan1 > 6000
  temp_exceeded = \
    check_temp(sensors.temp_exhaust, MAX_EXHAUST_TEMP, "Exhaust") or \
    check_temp(sensors.temp_cpu1, MAX_CPU_TEMP, "CPU1") or \
    check_temp(sensors.temp_cpu2, MAX_CPU_TEMP, "CPU2")

  if temp_exceeded:
    level = logging.INFO if not fan_control else logging.DEBUG
    log(level, "  Turning on fan control")
    set_fan_control(True)
    db_insert("INSERT INTO FanControl VALUES(CURRENT_TIMESTAMP, 0, TRUE)", None)
  else:
    temp = int(max(sensors.temp_cpu1, sensors.temp_cpu2))
    fan_power = FAN_SPEED_MAP.get(temp)
    if fan_power is not None:
      log(logging.INFO, "  Max CPU temp is %d. Setting fan speed to %d%%" % (temp, fan_power))
    else:
      fan_power = sorted(FAN_SPEED_MAP.values())[0]
      log(logging.INFO, "  Max CPU temp is %d. Setting fan speed to lowest setting %d%%" % (temp, fan_power))

    set_fan_control(False)
    set_fan_power(fan_power)
    db_insert("INSERT INTO FanControl VALUES(CURRENT_TIMESTAMP, ?, FALSE)", [fan_power])

  time.sleep(10)
  log_sensors(read_sensors())


def execute(command):
  log(logging.DEBUG, "  %s" % command)
  result = subprocess.run(command.split(), stdout=subprocess.PIPE)
  if result.returncode != 0:
    raise Exception("Failed to execute '%s'" % command)
  return result.stdout.decode("utf-8")


def read_sensors():
  lines = execute("ipmitool sensor").splitlines()
  inlet_temp = None
  exhaust_temp = None
  cpu1_temp = None
  cpu2_temp = None
  fan1_speed = None
  fan2_speed = None
  fan3_speed = None
  fan4_speed = None
  fan5_speed = None
  fan6_speed = None

  for line in lines:
    split = line.split("|")
    name = split[0].strip()
    value = split[1].strip()

    if name == "Inlet Temp":
      inlet_temp = int(float(value))
    elif name == "Exhaust Temp":
      exhaust_temp = int(float(value))
    elif name == "Temp":
      if cpu1_temp is None:
        cpu1_temp = int(float(value))
      else:
        cpu2_temp = int(float(value))
    elif name == "Fan1 RPM":
      fan1_speed = int(float(value))
    elif name == "Fan2 RPM":
      fan2_speed = int(float(value))
    elif name == "Fan3 RPM":
      fan3_speed = int(float(value))
    elif name == "Fan4 RPM":
      fan4_speed = int(float(value))
    elif name == "Fan5 RPM":
      fan5_speed = int(float(value))
    elif name == "Fan6 RPM":
      fan6_speed = int(float(value))

  return Sensors(inlet_temp, exhaust_temp, cpu1_temp, cpu2_temp, fan1_speed, fan2_speed, fan3_speed, fan4_speed,
                 fan5_speed,
                 fan6_speed)


def set_fan_control(enabled):
  execute("ipmitool raw 0x30 0x30 0x01 %s" % ("0x01" if enabled else "0x00"))


def set_fan_power(percent):
  execute("ipmitool raw 0x30 0x30 0x02 0xff 0x%02x" % percent)


def log_sensors(sensors):
  log(logging.INFO,
      "  Sensors: Intel: %dc Exhaust: %dc CPU1: %dc CPU2: %dc Fans: ~%d rpm"
      % (sensors.temp_inlet, sensors.temp_exhaust, sensors.temp_cpu1, sensors.temp_cpu2, sensors.rpm_fan1))
  db_insert(
    "INSERT INTO Sensors VALUES(CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [sensors.temp_inlet,
     sensors.temp_exhaust,
     sensors.temp_cpu1,
     sensors.temp_cpu2,
     sensors.rpm_fan1,
     sensors.rpm_fan2,
     sensors.rpm_fan3,
     sensors.rpm_fan4,
     sensors.rpm_fan5,
     sensors.rpm_fan6],
  )


def db_insert(sql, params):
  if db is not None:
    db.execute(sql, params)
    db.commit()


def check_temp(temp, max_temp, name):
  if temp > max_temp:
    log(logging.INFO, "  %s temp %d exceeded %d" % (name, temp, max_temp))
    return True
  return False


def log(level, message):
  if logger is None:
    print(message)
  else:
    logger.log(level, message)


def setup_logger(filename):
  if filename is not None:
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(filename, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    handler.setFormatter(logging.Formatter("%(asctime)s: %(levelname)-10s %(message)s"))
    logger.addHandler(handler)


if __name__ == '__main__':
  try:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", "-l", dest="log", default=None)
    parser.add_argument("--database", "-d", dest="database", default=None)
    args = parser.parse_args()
    if args.log is not None:
      logger = logging.getLogger("Dell PowerEdge 730xd Fan Control")
      setup_logger(args.log)
    if args.database is not None:
      db = sqlite3.connect(args.database)

    main()
  except:
    log(logging.ERROR, "Unexpected error: %s" % sys.exc_info()[0])
    log(logging.WARN, "Turning on auto fan control")
    set_fan_control(True)
    raise
  finally:
    if db is not None:
      db.close()
