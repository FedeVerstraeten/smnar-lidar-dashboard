#!/usr/bin/env python3

"""
This class will:
- open a connection
- configure a TR
- start the acquisition, wait for one sec
- read from the TR the analog and photon counting data back
- dump the data into a file
"""

# Sys libraries
import os
import sys
# __dir__ = os.path.dirname(__file__)
# path = os.path.join(__dir__,'packages')
# sys.path.insert(0,path)

# Libraries
import time
import socket
import numpy as np

## Input Ranges
MILLIVOLT500 = 0
MILLIVOLT100 = 1
MILLIVOLT20  = 2

## Threshold Modes
THRESHOLD_LOW  = 0
THRESHOLD_HIGH = 1

## Datasets
PHOTON = 0
LSW    = 1
MSW    = 2

## Memory
MEM_A = 0
MEM_B = 1

class licelcontroller:

  # ATTRIBUTES:

  def __init__(self):

    # TCP/IP socket
    self.host = '10.49.234.234'
    self.port = 2055
    self.sock = None
    self.buffersize = 2*(4096+1) # 2bytes/bin * 4096+1 bin = 8194 bytes = 8kb + 2kb

    # Licel parameters
    #self.transient_recorder = 0 
    self.bin_long_trace = 4000
    self.shots_delay = 10000 # wait 10s = 300shots/30Hz
    self.timeout = 5 # seconds

    # Status parameters
    self.memory = 0
    self.acquisition_state = False
    self.recording = False
    self.shots_number = 0

    # Data
    # self.analog_dataset = None
    # self.clip = None
    # self.normalized_dataset = None

  # METHODS:
  
  def openConnection(self,host,port):
    server_address = (host,port)
    
    if self.sock is None:
      self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    try:
      print('Connecting to: ', server_address)
      self.sock.connect(server_address)
      print('Connected to server')
    except Exception as e:
      raise ValueError("Connection to server failed")

  def closeConnection(self):
    try:
      print('Closing connecting to: ', (self.host,self.port))
      self.sock.shutdown(socket.SHUT_RDWR)
      self.sock.close()
      self.sock = None
      print('Connection closed')
    except Exception as e:
      raise ValueError("Connection to server failed")

  def runCommand(self,command,wait):
    response=None
    try:
      print('Sending:',command)
      self.sock.send(bytes(command + '\r\n','utf-8'))
      self.sock.settimeout(self.timeout)
      
      if wait!=0:
        time.sleep(wait) # wait TCP acquisition
      
      response = self.sock.recv(self.buffersize).decode()
      print(f"Received from server: {response} msg len: {len(response)}")

    except Exception as e:
      raise e
    finally:
      return response

  def selectTR(self,transientrecorder):
    command = "SELECT" + " " + str(transientrecorder)
    waitsecs = 0
    response = self.runCommand(command,waitsecs)
  
    if "executed" not in response:
      print("Licel_TCPIP_SelectTR - Error 5083:", command)
      return -5083
    else:
      return 0

  def setInputRange(self,inputrange):
    command = "RANGE"+ " " + str(inputrange)
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "set to" not in response:
      print("Licel_TCPIP_SetInputRange - Error 5097:", command)
      return -5097
    else:
      return 0

  def setThresholdMode(self,thresholdmode):
    command = "THRESHOLD"+ " " + str(thresholdmode)
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "THRESHOLD" not in response:
      print("Licel_TCPIP_SetThresholdMode - Error 5098:", command)
      return -5098
    else:
      return 0

  def setDiscriminatorLevel(self,discriminatorlevel):
    command = "DISC"+ " " + str(discriminatorlevel)
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "set to" not in response:
      print("Licel_TCPIP_SetDiscriminatorLevel - Error 5096:", command)
      return -5096
    else:
      return 0

  def clearMemory(self):
    command = "CLEAR"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "executed" not in response:
      print("Licel_TCPIP_ClearMemory - Error 5092:", response)
      return -5092
    else:
      return 0

  def startAcquisition(self):
    command = "START"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "executed" not in response:
      print("Licel_TCPIP_SingleShot - Error 5095:", response)
      return -5095
    else:
      return 0

  def stopAcquisition(self):
    command = "STOP"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "executed" not in response:
      print("Licel_TCPIP_SingleShot - Error 5095:", response)
      return -5095
    else:
      return 0

  def getStatus(self):
  # def parseStatus(sock):
    command = "STAT?"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "Shots" in response:
      self.shots_number = int(response.split()[1])
      
      if "Armed" in response:
        self.acquisition_state = True
        self.recording = True

      if "MemB" in response:
        self.memory = 1

      #TODO class attributes STAT
      # return shots_number,memory,acquisition_state,recording 
      return 0

    else:
      self.memory = 0
      self.acquisition_state = False
      self.recording = False
      self.shots_number = 0

      print("Licel_TCPIP_GetStatus - Error 5765:", response)
      return -5765

  def getDatasets(self,device,dataset,bins,memory):

    command = "DATA?" + " " + str(device) \
                      + " " + str(bins) \
                      + " " + str(dataset) \
                      + " " + str(memory)
    
    delay = 0.25 # seconds
    databuff=b'0'
    
    # resize buffer
    if self.buffersize < 2*bins:
      self.buffersize = 2*bins

    try:
      while(len(databuff) < 2*bins and delay<10): # 1bin = 2 bytes = 16 bits
        self.sock.send(bytes(command + '\r\n','utf-8'))
        self.sock.settimeout(self.timeout)
        time.sleep(delay) # wait TCP acquisition 
      
        databuff = self.sock.recv(self.buffersize)
        print("databuff len:",len(databuff))
        delay += 1

    except Exception as e:
      raise e
    
    dataout = np.frombuffer(databuff,dtype=np.uint16)

    return dataout

  def combineAnalogDatasets(self,i_lsw,i_msw):
    MSW_ACUM_MASK=0x00FF
    LSW_CLIP_MASK=0x0100

    accum=np.zeros(len(i_msw)-1,np.uint32)
    msw_aux=np.array(i_msw,dtype=np.uint32)
    lsw_aux=np.array(i_lsw,dtype=np.uint32)

    # concat lower 8bit of MSW with LSW
    # MSW(8bit) + LSW(16bit) = 24bit
    for i in range(1,len(i_msw)):
      accum[i-1] = np.left_shift(msw_aux[i] & MSW_ACUM_MASK, 16) + lsw_aux[i]
    
    clip = np.right_shift(i_msw[1:] & LSW_CLIP_MASK, 8)

    # self.analog_dataset=accum.astype(np.float64)
    # self.clip=clip.astype(np.uint16)
   
    return accum.astype(np.float64),clip.astype(np.uint16)

  def normalizeData(self,analog_dataset,cycles):

    if cycles==0:
      normalized_dataset=np.array(analog_dataset,dtype=np.float64)
    else:
      normalized_dataset=np.array(analog_dataset,dtype=np.float64)/cycles
      
    # self.normalized_dataset = normalized_dataset

    return normalized_dataset

  def scaleAnalogData(self,normalized_dataset,inputrange):

    # 2^12 = 4096 bits max Licel ADC counts
    
    scale = 0.0

    if inputrange == MILLIVOLT500:
      scale=500.0/4096.0
    elif inputrange == MILLIVOLT100:
      scale=100.0/4096.0
    elif inputrange == MILLIVOLT20:
      scale=20.0/4096.0
    else:
      scale=1.0

    # scaling 
    scaled_dataset = np.array(normalized_dataset)*scale
    
    return scaled_dataset

  def msDelay(self,delay):
    time.sleep(delay/1000) # delay on miliseconds

  # def waitForReady(self,wait):
  #   pass

  def getAnalogSignalmV(self,tr,bin,memory,inputrange):
    pass
    # # get the shotnumber 
    # if lc.getStatus() == 0:
    #   if (lc.shots_number > 1):
    #     cycles = lc.shots_number - 2 # WHY??!

    # # read from the TR triggered mem A
    # data_lsw = lc.getDatasets(tr,"LSW",BIN_LONG_TRANCE+1,"A")
    # data_msw = lc.getDatasets(tr,"MSW",BIN_LONG_TRANCE+1,"A")

    # # combine, normalize an scale data to mV
    # data_accu,data_clip = lc.combineAnalogDatasets(data_lsw, data_msw)
    # data_phys = lc.normalizeData(data_accu,cycles)
    # data_mv = lc.scaleAnalogData(data_phys,licelsettings.MILLIVOLT500) 
    # return data_mv

  def unselectTR(self):
    command = "SELECT -1"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)
  
    if "executed" not in response:
      print("Licel_TCPIP_SelectTR - Error 5083:", command)
      return -5083
    else:
      return 0

  def multipleClearMemory(self):
    command = "MCLEAR"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "executed" not in response:
      print("Licel_TCPIP_MultipleClearMemory - Error 5080", response)
      return -5080
    else:
      return 0

  def multipleStart(self):
    command = "MSTART"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "executed" not in response:
      print("Licel_TCPIP_MultipleStart - Error 5086:", response)
      return -5086
    else:
      return 0

  def multipleStop(self):
    command = "MSTOP"
    waitsecs = 0
    response = self.runCommand(command,waitsecs)

    if "executed" not in response:
      print("Licel_TCPIP_MultipleStopAcqusition - Error 5082:", response)
      return -5082
    else:
      return 0
