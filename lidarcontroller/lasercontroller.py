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

  def connect(self,port=None,baudrate=None,timeout = None):
    if self.isConnected():
      print("Serial connection already open to port:",self.serialcom.port)
      return

    try:
      if port is not None:
        self.serialcom.port = port
      if baudrate is not None:
        self.serialcom.baudrate = baudrate
      if timeout is not None:
        self.serialcom.timeout = timeout

      self.serialcom.open()
    except Exception as ex:
      raise ValueError("Unable to start serial port. Please check the connection and the permissions.") from ex
    else:
      print("Serial connection established to port:",self.serialcom.port)

  def disconnect(self):
    self.clearBuffers()

    try:
      if self.serialcom.isOpen():
        self.serialcom.close()
    except Exception as ex:
      raise ValueError("Unable to close serial port.") from ex
    else:
      print("Serial Port " + self.serialcom.port + " closed")

  def isConnected(self):
    return self.serialcom.isOpen()

  def clearBuffers(self):
    if self.serialcom.isOpen():
      try:
        self.serialcom.reset_input_buffer()
        self.serialcom.reset_output_buffer()
      except Exception:
        print("Unable to clear laser serial buffers")

  def sendCommand(self, command):
    if not self.serialcom.isOpen():
      raise ValueError("Laser serial port is not connected.")

    self.serialcom.write((command + '\r').encode('ascii'))

  def queryCommand(self, command):
    if not self.serialcom.isOpen():
      raise ValueError("Laser serial port is not connected.")

    self.clearBuffers()
    self.sendCommand(command)
    response = self.serialcom.read_until(b'\r').decode('ascii', errors='replace').strip()

    if not response:
      raise ValueError("Laser did not return a response.")

    return response

  def startLaser(self):
    if self.serialcom.isOpen():
      print("START Laser")
      self.sendCommand('ST 1')
      print("Laser on")
      time.sleep(1)
      self.sendCommand('SH 1')
      print("Shutter opened")
    else:
      raise ValueError("Laser serial port is not connected.")

  def stopLaser(self):
    if self.serialcom.isOpen():
      print("STOP Laser")
      self.sendCommand('SH 0')
      print("SHUTTER closed")
      time.sleep(1)
      self.sendCommand('ST 0')
      print("Laser off")
    else:
      raise ValueError("Laser serial port is not connected.")

  def shotsCounter(self):
    response = self.queryCommand('SC')

    if len(response) != 9 or not response.isdigit():
      raise ValueError("Unexpected shot counter response: " + response)

    return int(response)

  # def singleShot(self):
  #   if self.serialcom.isOpen():
  #     print("Single shot" )      
  #     shots = self.serialcom.write(b'SS\r')
