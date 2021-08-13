import sys
import os
import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

args = sys.argv
data_path = args[1]
url = args[2]
authorization = {"Authorization": args[3]}

delete_flag = True

with open(data_path, newline='') as data:
    files = {'file': data.read(),
             'csv_ver': args[13],
             'data_name': args[4],
             'data_height_ft': args[5],
             'data_height_in': args[6],
             'data_weight': args[7],
             'data_age_year': args[8],
             'data_age_month': args[9],
             'data_sleep_status': args[10],
             'data_sex': args[11],
             'timeStamp': args[14],
             'file_part': args[12], }
    print('POSTing raw data to server')
    try:
        r = requests.post(url, json=files, headers=authorization, verify=False)
        print('Response Status Code: {0}\nResponse Message: {1}'.format(r.status_code, json.loads(r.text)['message']))
    except Exception as e:
        print('\n\nError on post data:\n{0}'.format(e))
        # keep file on mvp
        delete_flag = False
        pass

    if delete_flag:
        os.remove(data_path)
