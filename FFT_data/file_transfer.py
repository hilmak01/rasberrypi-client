import sys
import os
import json
import requests
import ast
import datetime

args=sys.argv
data_path = args[1]
url = args[2]
authorization={"Authorization":args[3]}
print_debugs = True

if os.path.exists('/home/root/FFT_data/dummy.bin') == False:
    f=open('/home/root/FFT_data/dummy.bin','wb+') # create a dummy file to be used when sending FFT data
    f.close()

dummy_file=data_path+'dummy.bin'
files={'file': open(dummy_file,'rb')} # start the dictionary with a dummy file that won't be sent
for f in os.listdir(data_path):
    if "ready.bin" in f: # look for files that the c app has labeled as ready to send to the server
        now=datetime.datetime.now()
        f_new=data_path+str(now.date())+"_"+str(now.time())+f # prepend the filename with a timestamp; for now use the default time zone
        os.rename(data_path+f,f_new)
        files['file'] = open(f_new,'rb')

        # r=requests.post(url,files=files,headers=headers) # build up the file tuple first, then call this once to send them all
        r=requests.post(url,files=files,headers=authorization)
        if print_debugs:
            print("File sent to server: ",f_new)
        os.remove(f_new) # delete the file; SPI C app will create it again when it's needed
