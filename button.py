#!/usr/bin/python3

import time
from gpiozero import LED, Button
from timeit import default_timer as timer
import os

class RadarControl:
    def __init__(self):
        self.led = LED(24)
        self.led.off()
        self.button = Button(25)
        self.btnCtrl = 0
        self.btnTime = 0
        self.btnGap = 0
        self.btnElapsed = 0
        self.button.when_pressed = self.btnOn
        self.button.when_released = self.btnOff

    def btnOn(self):
        if self.btnCtrl == 0 or self.btnCtrl == 2:
            print("Pressed ", self.btnCtrl)
            self.btnTime = timer()
            if self.btnCtrl == 0:
                self.btnCtrl = 1
            else:
                if (timer() - self.btnGap) < 2:
                    self.btnCtrl = 3
                else:
                    self.btnCtrl = 0;
                    self.led.off()
        else:
            self.btnCtrl = 0
            self.led.off()

    def btnOff(self):
        if self.btnCtrl == 1 or self.btnCtrl == 3:
            print("Released ", self.btnCtrl)
            print 
            self.btnElapsed = timer() - self.btnTime
            if self.btnElapsed > 0.1 and self.btnElapsed < 1.3:
                # Click detected
                if self.btnCtrl == 1:
                    self.btnCtrl = 2    # Go for second click
                    self.btnGap = timer()
                else:
                    self.btnCtrl = 0
                    self.led.on()
                    time.sleep(3)                  # Allow reset to take effect
#                    self.led.off()
                    os.system("sudo shutdown now")
                    
            else:
                self.led.off()
                self.btnCtrl = 0
        else:
            self.btnCtrl = 0
            self.led.off()

RDRControl = RadarControl()
# ------------------------------------------------------------------------------
print("Button.py started")
while True:
    time.sleep(100)  # so it wont coincide with Radar process

