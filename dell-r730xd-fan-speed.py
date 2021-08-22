#!/usr/bin/python
#
import argparse
import logging
import subprocess
from collections import namedtuple
from logging.handlers import RotatingFileHandler

MAX_EXHAUST_TEMP = 35.0
MAX_CPU_TEMP = 45.0
FAN_SPEED_PERCENT = 20

LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

logger = None

Sensors = namedtuple("Sensors", [
  "exhaustTemp",
  "cpu1Temp",
  "cpu2Temp",
  "fan1Speed",
  "fan2Speed",
  "fan3Speed",
  "fan4Speed",
  "fan5Speed",
  "fan6Speed",
])


def execute(command):
  log(logging.DEBUG, "  %s" % command)
  result = subprocess.run(command.split(), stdout=subprocess.PIPE)
  if result.returncode != 0:
    raise Exception("Failed to execute '%s'" % command)
  return result.stdout.decode("utf-8")


def read_sensors():
  lines = execute("ipmitool sensor").splitlines()
  exhaustTemp = None
  cpu1Temp = None
  cpu2Temp = None
  fan1Speed = None
  fan2Speed = None
  fan3Speed = None
  fan4Speed = None
  fan5Speed = None
  fan6Speed = None

  for line in lines:
    split = line.split("|")
    name = split[0].strip()
    value = split[1].strip()

    if name == "Exhaust Temp":
      exhaustTemp = float(value)
    elif name == "Temp":
      if cpu1Temp is None:
        cpu1Temp = float(value)
      else:
        cpu2Temp = float(value)
    elif name == "Fan1 RPM":
      fan1Speed = float(value)
    elif name == "Fan2 RPM":
      fan2Speed = float(value)
    elif name == "Fan3 RPM":
      fan3Speed = float(value)
    elif name == "Fan4 RPM":
      fan4Speed = float(value)
    elif name == "Fan5 RPM":
      fan5Speed = float(value)
    elif name == "Fan6 RPM":
      fan6Speed = float(value)

  return Sensors(exhaustTemp, cpu1Temp, cpu2Temp, fan1Speed, fan2Speed, fan3Speed, fan4Speed, fan5Speed, fan6Speed)


def set_fan_control(enabled):
  execute("ipmitool raw 0x30 0x30 0x01 %s" % ("0x01" if enabled else "0x00"))


def set_fan_speed(percent):
  execute("ipmitool raw 0x30 0x30 0x02 0xff 0x%02x" % percent)


def log_sensors(sensors):
  log(
    logging.INFO,
    "  Sensors: %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f"
    % (
      sensors.exhaustTemp,
      sensors.cpu1Temp,
      sensors.cpu2Temp,
      sensors.fan1Speed,
      sensors.fan2Speed,
      sensors.fan3Speed,
      sensors.fan4Speed,
      sensors.fan5Speed,
      sensors.fan6Speed,
    ))


def check_temp(temp, maxTemp, fan_control):
  if temp > maxTemp:
    if not fan_control:
      level = logging.INFO if not fan_control else logging.DEBUG
      log(level, "  Exhaust temp %0.1f exceeded %0.1f" % (temp, maxTemp))
    return True
  return False


def log(level, message):
  if logger is None:
    print(message)
  else:
    logger.log(level, message)


def main():
  log(logging.INFO, "Reading sensors:")
  sensors = read_sensors()
  log_sensors(sensors)

  fan_control = sensors.fan1Speed > 6000
  temp_exceeded = \
    check_temp(sensors.exhaustTemp, MAX_EXHAUST_TEMP, fan_control) or \
    check_temp(sensors.cpu1Temp, MAX_CPU_TEMP, fan_control) or \
    check_temp(sensors.cpu2Temp, MAX_CPU_TEMP, fan_control)

  if temp_exceeded:
    level = logging.INFO if not fan_control else logging.DEBUG
    log(level, "  Turning on fan control")
    set_fan_control(True)
  else:
    level = logging.INFO if fan_control else logging.DEBUG
    log(level, "  Turning off fan control and setting speed to %s%%" % FAN_SPEED_PERCENT)
    set_fan_control(False)
    set_fan_speed(FAN_SPEED_PERCENT)

def setup_logger(filename):
  if filename is not None:
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(filename, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    handler.setFormatter(logging.Formatter("%(asctime)s: %(levelname)-10s %(message)s"))
    logger.addHandler(handler)


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("--log", "-l", dest="log", default=None)
  args = parser.parse_args()
  logger = logging.getLogger("Dell PowerEdge 730xd Fan Control")
  setup_logger(args.log)

  main()
