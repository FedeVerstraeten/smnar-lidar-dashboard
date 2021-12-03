#!/usr/bin/env python3

# Libraries
import serial  #Serial comunication
import time 

class laserController:

  def __init__(self, port = "COM3", baudrate = 9600, timeout = 5):
    self.serialcom = serial.Serial()
    self.serialcom.port = port
    self.serialcom.baudrate = baudrate
    self.serialcom.timeout = timeout
    self.serialcom.bytesize = serial.EIGHTBITS # 8bits
    self.serialcom.parity = serial.PARITY_NONE # no parity
    self.serialcom.stopbits = serial.STOPBITS_ONE # 1 stop bit (8N1)

  def connect(self,port="COM3",baudrate=9600,timeout = 5):
    try:
      self.serialcom.port = port
      self.serialcom.baudrate = baudrate
      self.serialcom.timeout = timeout

      self.serialcom.open()
    except Exception as ex:
      raise ValueError("Unable to start serial port. Please check the connection and the permissions.")
      sys.exit()
    else:
      print("Serial connection established")

  def disconnect(self):
    try:
      self.serialcom.close()
    except Exception as ex:
      raise ValueError("Unable to close serial port.")
      sys.exit()
    else:
      print("Serial Port " + self.serialcom.port + " closed")

  def startLaser(self):
    if self.serialcom.isOpen():
      print("START Laser")
      self.serialcom.write(b'ST 1')
      print("Laser on")
      time.sleep(1)
      self.serialcom.write(b'SH 1')
      print("Shutter opened")

  def stopLaser(self):
    if self.serialcom.isOpen():
      print("STOP Laser")
      self.serialcom.write(b'SH 0')
      print("SHUTTER closed")
      time.sleep(1)
      self.serialcom.write(b'ST 0')
      print("Laser off")

  def shotsCounter(self):
    if self.serialcom.isOpen():
      shots = self.serialcom.write(b'SC')
      print("Shot counter = ",shots)

  def singleShot(self):
    if self.serialcom.isOpen():
      print("Single shot" )      
      shots = self.serialcom.write(b'SC')
