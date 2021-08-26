--Fan1 RPM         | 6000.000   | RPM        | ok    | na        | 360.000   | 600.000   | na        | na        | na
--Fan2 RPM         | 6000.000   | RPM        | ok    | na        | 360.000   | 600.000   | na        | na        | na
--Fan3 RPM         | 5880.000   | RPM        | ok    | na        | 360.000   | 600.000   | na        | na        | na
--Fan4 RPM         | 5880.000   | RPM        | ok    | na        | 360.000   | 600.000   | na        | na        | na
--Fan5 RPM         | 5880.000   | RPM        | ok    | na        | 360.000   | 600.000   | na        | na        | na
--Fan6 RPM         | 5880.000   | RPM        | ok    | na        | 360.000   | 600.000   | na        | na        | na
--Inlet Temp       | 30.000     | degrees C  | ok    | na        | -7.000    | 3.000     | 42.000    | 47.000    | na
--Exhaust Temp     | 35.000     | degrees C  | ok    | na        | 0.000     | 0.000     | 70.000    | 75.000    | na
--Temp             | 43.000     | degrees C  | ok    | na        | 3.000     | 8.000     | 95.000    | 100.000   | na
--Temp             | 40.000     | degrees C  | ok    | na        | 3.000     | 8.000     | 95.000    | 100.000   | na
--Fan Redundancy   | 0x0        | discrete   | 0x0180| na        | na        | na        | na        | na        | na

CREATE TABLE Sensors(
    timestamp INTEGER,
    temp_inlet INTEGER,
    temp_exhaust INTEGER,
    temp_cpu1 INTEGER,
    temp_cpu2 INTEGER,
    rpm_fan1 INTEGER,
    rpm_fan2 INTEGER,
    rpm_fan3 INTEGER,
    rpm_fan4 INTEGER,
    rpm_fan5 INTEGER,
    rpm_fan6 INTEGER
);

CREATE TABLE FanControl(
    timestamp INTEGER,
    percent INTEGER,
    auto INTEGER
);


