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
  
  IURL = "http://weather.uwyo.edu/cgi-bin/sounding?"
  FTYPE = "TYPE=TEXT%3ALIST&"

  reg = "region=" + region + "&"
  yr = "YEAR=" + date.split('-')[0] + "&"
  mon = "MONTH=" + date.split('-')[1] + "&"
  day_beg = "FROM=" + date.split('-')[2] + '00' + "&"
  day_end = "TO=" + date.split('-')[2] + '12' "&"
  st = "STNM=" + station
  url = IURL + reg + FTYPE + yr + mon + day_beg + day_end + st

  raw_html = gets_html(url)
  sounding_data = raw_html.split('<PRE>')[1].split('</PRE>')[0]

  with open('UWyoming_'+date+'_'+station,'w') as file:
    file.write(sounding_data)
