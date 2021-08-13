import serial
from time import sleep
from gpiozero import LED
from time import sleep

reset = LED(7)
sop0 = LED(8)

radarConfig = b"sensorStop\rflushCfg\rdfeDataOutputMode 1\rchannelCfg 1 1 0\radcCfg 2 1\radcbufCfg -1 0 0 1 0\rprofileCfg 0 60.25 7 6 57 0 0 60 1 100 2000 0 0 40\rchirpCfg 0 0 0 0 0 0 0 1\rframeCfg 0 0 2 0 10 1 0\rlowPower 0 1\rguiMonitor 0 0 0 0 1\rvitalSignsCfg 0 0.60 256 512 1 0.1 0.05 100000 300000\rmotionDetection 1 20 2.0 0\r"
radarStart = b"sensorStart\r"

sop0.on()                   # Makes SOP[0] high
print("Asserting reset")
reset.off()                 # Puts radar board to reset
sleep(0.1)                  # Allow reset to take effect
print("Deasserting reset")
reset.on()                  # Release radar from reset
sleep(1)                    # Wait for radar firmware to be ready

ser = serial.Serial('/dev/ttyS0', 115200, bytesize=8, parity='N', stopbits=1, timeout=None, xonxoff=0, rtscts=0)   # open serial port
print("Name: " + ser.name + "\n")           # check which port was really used
ser.write(radarConfig)                         # write a string
sleep(1)
ser.write(radarStart)                         # write a string
sleep(1)
ser.close()
ser = serial.Serial('/dev/ttyS0', 921600, bytesize=8, parity='N', stopbits=1, timeout=None, xonxoff=0, rtscts=0)   # open serial port
#ser.baudrate = 921600
#ser.write(b"hello")                        # write a string
while 1 == 1:
    dt = ser.read(10)
    print(dt)
ser.close()
