# LiDAR Rayleigh Fit
import pandas as pd
import numpy as np

from scipy import constants
from scipy import integrate
from scipy.interpolate import interp1d


class lidarSignal:
  
  def __init__(self):
  
    # raw signal
    self.__BIN_METERS = 7.5 # meters for each bin
    self.raw_signal=[]
    self.range = []
    self.bin_long_trace=0

    # range correction
    self.bin_offset = 0
    self.bin_threshold = 0
    self.bias = 0
    self.rc_signal = []

    # rayleigh fit
    self.wavelength = 532 # [nm]
    self.surface_temperature = 300 # [K]
    self.surface_pressure = 1024 # [hPa]
    self.masl = 5.0 # meters above sea level (AMSL)
    self.fit_init = 0 # [m]
    self.fit_final = 0 # [m]
    self.pr2_mol = []
    self.rms_err = 0
    self.adj_factor = 0

    self.__us_std_model = {
                            "height" : [0, 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 2600, 2800, 3000, 3200, 3400, 3600, 3800, 4000, 4200, 4400, 4600, 4800, 5000, 5200, 5400, 5600, 5800, 6000, 6200, 6400, 6600, 6800, 7000, 7200, 7400, 7600, 7800, 8000, 8200, 8400, 8600, 8800, 9000, 9200, 9400, 9600, 9800, 10000, 10200, 10400, 10600, 10800, 11000, 11200, 11400, 11600, 11800, 12000, 12200, 12400, 12600, 12800, 13000, 13200, 13400, 13600, 13800, 14000, 14200, 14400, 14600, 14800, 15000, 15200, 15400, 15600, 15800, 16000, 16200, 16400, 16600, 16800, 17000, 17200, 17400, 17600, 17800, 18000, 18200, 18400, 18600, 18800, 19000, 19200, 19400, 19600, 19800, 20000, 20200, 20400, 20600, 20800, 21000, 21200, 21400, 21600, 21800, 22000, 22200, 22400, 22600, 22800, 23000, 23200, 23400, 23600, 23800, 24000, 24200, 24400, 24600, 24800, 25000, 25200, 25400, 25600, 25800, 26000, 26200, 26400, 26600, 26800, 27000, 27200, 27400, 27600, 27800, 28000, 28200, 28400, 28600, 28800, 29000, 29200, 29400, 29600, 29800, 30000],
                            "temperature" : [288.15, 286.85, 285.55, 284.25, 282.95, 281.65, 280.35, 279.05, 277.75, 276.45, 275.15, 273.85, 272.55, 271.25, 269.95, 268.65, 267.35, 266.05, 264.75, 263.45, 262.15, 260.85, 259.55, 258.25, 256.95, 255.65, 254.35, 253.05, 251.75, 250.45, 249.15, 247.85, 246.55, 245.25, 243.95, 242.65, 241.35, 240.05, 238.75, 237.45, 236.15, 234.85, 233.55, 232.25, 230.95, 229.65, 228.35, 227.05, 225.75, 224.45, 223.15, 221.85, 220.55, 219.25, 217.95, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.65, 216.85, 217.05, 217.25, 217.45, 217.65, 217.85, 218.05, 218.25, 218.45, 218.65, 218.85, 219.05, 219.25, 219.45, 219.65, 219.85, 220.05, 220.25, 220.45, 220.65, 220.85, 221.05, 221.25, 221.45, 221.65, 221.85, 222.05, 222.25, 222.45, 222.65, 222.85, 223.05, 223.25, 223.45, 223.65, 223.85, 224.05, 224.25, 224.45, 224.65, 224.85, 225.05, 225.25, 225.45, 225.65, 225.85, 226.05, 226.25, 226.45, 226.65],
                            "pressure" : [1013.27, 989.48, 966.13, 943.24, 920.78, 898.77, 877.18, 856.01, 835.25, 814.91, 794.97, 775.43, 756.27, 737.51, 719.12, 701.1, 683.45, 666.17, 649.23, 632.65, 616.42, 600.52, 584.95, 569.72, 554.81, 540.21, 525.93, 511.95, 498.28, 484.9, 471.82, 459.02, 446.51, 434.27, 422.31, 410.62, 399.18, 388.01, 377.1, 366.43, 356.01, 345.83, 335.88, 326.17, 316.69, 307.43, 298.39, 289.57, 280.96, 272.56, 264.37, 256.37, 248.58, 240.97, 233.55, 226.33, 219.3, 212.49, 205.89, 199.5, 193.31, 187.31, 181.49, 175.86, 170.4, 165.11, 159.98, 155.01, 150.2, 145.54, 141.02, 136.64, 132.4, 128.29, 124.31, 120.45, 116.71, 113.08, 109.57, 106.17, 102.88, 99.68, 96.59, 93.59, 90.68, 87.87, 85.14, 82.5, 79.94, 77.45, 75.05, 72.72, 70.46, 68.27, 66.16, 64.1, 62.11, 60.18, 58.31, 56.5, 54.75, 53.05, 51.41, 49.81, 48.27, 46.78, 45.33, 43.94, 42.58, 41.27, 40, 38.77, 37.58, 36.42, 35.31, 34.22, 33.18, 32.16, 31.18, 30.23, 29.31, 28.41, 27.55, 26.71, 25.9, 25.11, 24.35, 23.61, 22.9, 22.2, 21.53, 20.88, 20.25, 19.64, 19.05, 18.47, 17.92, 17.38, 16.86, 16.35, 15.86, 15.39, 14.93, 14.48, 14.05, 13.63, 13.22, 12.83, 12.45, 12.08, 11.72]
                          }

    self.sounding_data = {
                            "height" : [],
                            "temperature" : [],
                            "pressure" : []
                         }

  def loadSignal(self,signal):
    if len(signal)>0:
      signal = np.insert(signal,0,0) # set zero signal
      self.raw_signal = np.array(signal)
      self.bin_long_trace = len(self.raw_signal) 

  def offsetCorrection(self,bin_offset):
    if bin_offset > 0:
      self.bin_offset = int(bin_offset)
      self.bin_long_trace = self.bin_long_trace - bin_offset
      self.raw_signal = self.raw_signal[self.bin_offset : ]

  def setThreshold(self,threshold_meters):
    if threshold_meters > 0:
      self.bin_threshold = int(threshold_meters/self.__BIN_METERS)

  def rangeCorrection(self,threshold_meters=0):
    
    # set theshold
    if self.bin_threshold == 0:
      self.bin_threshold = int(self.bin_long_trace/4)
    else:
      self.setThreshold(threshold_meters)

    # Height range on bins
    self.range = self.__BIN_METERS * np.arange(0,self.bin_long_trace,1)
    
    # bias calculation
    self.bias = np.mean(self.raw_signal[self.bin_threshold:])

    # range correction
    self.rc_signal = (self.raw_signal - self.bias)*(self.range**2)

  def smoothSignal(self,level):
    # smooth with square box
    if level > 0:
      box_points = int(level)
    else:
      box_points = 3 # default smooth
    
    # convolution 
    box = np.ones(box_points)/box_points
    self.rc_signal = np.convolve(self.rc_signal, box, mode='same')

  def setSurfaceConditions(self,temperature,pressure):
    # Input temperature on Celsius to Kelvin degrees
    temp_kelvin = constants.convert_temperature(temperature,'Celsius','Kelvin')
    if temp_kelvin > 0:
      self.surface_temperature = temp_kelvin

    # Pressure on hecto Pascal
    if pressure > 0:
      self.surface_pressure = pressure

  def molecularProfile(self,wavelength,masl,surface_temperature=0,surface_pressure=0):

    self.wavelength = wavelength
    self.masl = masl

    self.setSurfaceConditions(surface_temperature,surface_pressure)

    # Loading low resolution atmosphere profile data
    if( self.sounding_data["height"] \
        and self.sounding_data["temperature"] \
        and self.sounding_data["pressure"]):

      height_lowres = self.sounding_data["height"]
      temperature_lowres = self.sounding_data["temperature"]
      pressure_lowres = self.sounding_data["pressure"]

    else:
      height_lowres = self.__us_std_model["height"]
      temperature_lowres = self.__us_std_model["temperature"]
      pressure_lowres = self.__us_std_model["pressure"]

    # High resolution height vector definition from MASL
    height_highres = self.masl + np.arange(0, self.bin_long_trace*self.__BIN_METERS, self.__BIN_METERS)

    # Interpolation Spline 1D cubic
    temperature_spline = interp1d(height_lowres, temperature_lowres, kind='cubic',fill_value='extrapolate')
    pressure_spline = interp1d(height_lowres, pressure_lowres, kind='cubic',fill_value='extrapolate')
    
    # Defining high resolution Temperature & Pressure vectors since MASL (LiDAR)
    temperature_highres = temperature_spline(height_highres)
    pressure_highres = pressure_spline(height_highres)

    # Profile scaling with current surface temperature and pressure conditions
    temperature_highres = self.surface_temperature * (temperature_highres/temperature_highres[0])
    pressure_highres = self.surface_pressure * (pressure_highres/pressure_highres[0])    

    # atmospheric molecular concentration
    kboltz = constants.k
    nmol = (100*pressure_highres)/(temperature_highres*kboltz)

    # alpha & beta coefficients
    beta_mol = nmol * ((550/self.wavelength)**4.09) * 5.45e-32
    alpha_mol = beta_mol * (8*np.pi/3)
  
    # Range vector referenced to the LiDAR level
    range_lidar = height_highres - self.masl

    cumtrapz = integrate.cumtrapz(alpha_mol, range_lidar, initial=0)
    tm2r_mol = np.exp(-2*cumtrapz)

    # Purely molecular atmosphere profile
    self.pr2_mol = beta_mol*tm2r_mol

  def loadSoundingData(self,height,temperature,pressure):
    
    if height!=[] and temperature!=[] and pressure!=[]:
      
      print(height[0],type(height[0]))  
      self.sounding_data["height"]=height
      self.sounding_data["temperature"]=temperature
      self.sounding_data["pressure"]=pressure

  def clearSoundingData(self):
    
    self.sounding_data["height"]=[]
    self.sounding_data["temperature"]=[]
    self.sounding_data["pressure"]=[]

  def rayleighFit(self,fit_init,fit_final):

    self.fit_init = fit_init
    self.fit_final = fit_final
    bin_init = int(fit_init/self.__BIN_METERS)
    bin_fin = int(fit_final/self.__BIN_METERS)
    

    # Adjusment factor calculus between elastic LiDAR and molecular signals
    # a = sum(Sel*Sm)/sum(Sm^2)


    sum_sel_sm = np.dot(self.rc_signal[bin_init:bin_fin+1],self.pr2_mol[bin_init:bin_fin+1])
    sum_sm_square = np.dot(self.pr2_mol[bin_init:bin_fin+1],self.pr2_mol[bin_init:bin_fin+1])

    self.adj_factor = sum_sel_sm/sum_sm_square
   
    # area low height 
    LH_OFFSET = 500 # meters
    bin_lh_offset = int(LH_OFFSET/self.__BIN_METERS)
    area_lh = np.sum(np.abs(self.rc_signal[bin_lh_offset:bin_init] - self.adj_factor * self.pr2_mol[bin_lh_offset:bin_init]))

    # Minimizing the RMS error
    sum_diff = self.rc_signal[bin_init:bin_fin+1] - self.adj_factor * self.pr2_mol[bin_init:bin_fin+1]
    dr = fit_final - fit_init
    self.rms_err = (np.sqrt((1/dr) * np.dot(sum_diff,sum_diff)))/area_lh

