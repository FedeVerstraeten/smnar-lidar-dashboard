import os
import re
import urllib
from urllib.error import URLError, HTTPError

# function to read html code from url
def gets_html(url):
    # Read  the url and return  html code
    try:
        req = urllib.request.Request(url,
                                     headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}
                                     )
        html = urllib.request.urlopen(req).read().decode("utf-8")
    except HTTPError as e:
        print('The server couldn\'t fulfill the SOUNDING requested.')
        print('Error code: ', e.code)
        html = ""
        pass
    except URLError as e:
        print('We failed to reach the server /weather.uwyo.edu.')
        print('Reason: ', e.reason)
        html = ""
        pass
    finally:
        pass
    return html

# sounding data download from University of Wyoming
def download_sounding(station,region,date):
  header_info = ""
  sounding_data = ""
 
  # set up the url
  IURL = "http://weather.uwyo.edu/cgi-bin/sounding?"
  FTYPE = "TYPE=TEXT%3ALIST&"

  reg = "region=" + region + "&"
  yr = "YEAR=" + date.split('-')[0] + "&"
  mon = "MONTH=" + date.split('-')[1] + "&"
  day_beg = "FROM=" + date.split('-')[2] + '00' + "&"
  day_end = "TO=" + date.split('-')[2] + '12' "&"
  st = "STNM=" + station
  url = IURL + reg + FTYPE + yr + mon + day_beg + day_end + st

  # parsing html response
  raw_html = gets_html(url)

  # header info
  if(raw_html.find('<H2>') != -1):
    header_info = raw_html.split('<H2>')[1].split('</H2>')[0]

  # sounding raw data
  if(raw_html.find('<PRE>') != -1):
    sounding_data = raw_html.split('<PRE>')[1].split('</PRE>')[0]

  return header_info,sounding_data

# parse the sounding data download to csv list
def parse_sounding(sounding_data):
  HEADER_END=5
  parsed_data=[]

  if sounding_data != []:
    lines = sounding_data.splitlines(True)
    for line in lines[HEADER_END:]:
      line_csv = re.sub("\s+", ",", line.strip())
      parsed_data.append(line_csv)

  return parsed_data

# get radiosonde data: height, temperature, pressure
def get_htp(sounding_data):
  pressure = []
  height = []
  temperature = []

  parsed_data = parse_sounding(sounding_data)

  for line in parsed_data:
    pressure.append(line.split(',')[0])
    height.append(line.split(',')[1])
    temperature.append(line.split(',')[2])

  return height,temperature,pressure

