#!/usr/bin/python
#
import argparse
import logging
import subprocess
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

def main():
  log(logging.INFO, "Reading sensors:")
  sensors = read_sensors()
  log_sensors(sensors)

  fan_control = sensors.fan1Speed > 6000
  temp_exceeded = \
    check_temp(sensors.exhaustTemp, MAX_EXHAUST_TEMP, "Exhaust") or \
    check_temp(sensors.cpu1Temp, MAX_CPU_TEMP, "CPU1") or \
    check_temp(sensors.cpu2Temp, MAX_CPU_TEMP, "CPU2")

  if temp_exceeded:
    level = logging.INFO if not fan_control else logging.DEBUG
    log(level, "  Turning on fan control")
    set_fan_control(True)
  else:
    temp = int(max(sensors.cpu1Temp, sensors.cpu2Temp))
    fan_speed = FAN_SPEED_MAP.get(temp)
    if fan_speed is not None:
      log(logging.INFO, "  Max CPU temp is %d. Setting fan speed to %d%%" % (temp, fan_speed))
      set_fan_control(False)
      set_fan_speed(fan_speed)
    else:
      fan_speed = sorted(FAN_SPEED_MAP.values())[0]
      log(logging.INFO, "  Max CPU temp is %d. Setting fan speed to lowest setting %d%%" % (temp, fan_speed))

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

    if name == "Exhaust Temp":
      exhaust_temp = float(value)
    elif name == "Temp":
      if cpu1_temp is None:
        cpu1_temp = float(value)
      else:
        cpu2_temp = float(value)
    elif name == "Fan1 RPM":
      fan1_speed = float(value)
    elif name == "Fan2 RPM":
      fan2_speed = float(value)
    elif name == "Fan3 RPM":
      fan3_speed = float(value)
    elif name == "Fan4 RPM":
      fan4_speed = float(value)
    elif name == "Fan5 RPM":
      fan5_speed = float(value)
    elif name == "Fan6 RPM":
      fan6_speed = float(value)

  return Sensors(exhaust_temp, cpu1_temp, cpu2_temp, fan1_speed, fan2_speed, fan3_speed, fan4_speed, fan5_speed, fan6_speed)


def set_fan_control(enabled):
  execute("ipmitool raw 0x30 0x30 0x01 %s" % ("0x01" if enabled else "0x00"))


def set_fan_speed(percent):
  execute("ipmitool raw 0x30 0x30 0x02 0xff 0x%02x" % percent)


def log_sensors(sensors):
  log(
    logging.INFO,
    "  Sensors: %0.1f %0.1f %0.1f %0.1f"
    % (
      sensors.exhaustTemp,
      sensors.cpu1Temp,
      sensors.cpu2Temp,
      sensors.fan1Speed,
    ))


def check_temp(temp, max_temp, name):
  if temp > max_temp:
    log(logging.INFO, "  %s temp %0.1f exceeded %0.1f" % (name, temp, max_temp))
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
  parser = argparse.ArgumentParser()
  parser.add_argument("--log", "-l", dest="log", default=None)
  args = parser.parse_args()
  if args.log is not None:
    logger = logging.getLogger("Dell PowerEdge 730xd Fan Control")
    setup_logger(args.log)

  main()
