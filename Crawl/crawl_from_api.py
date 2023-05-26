#!pip install pycrypto

import re
import ast
import math
import json
import hashlib
import gspread
import requests
import datetime
import traceback
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from google.colab import auth
from IPython.display import clear_output 
from dateutil.relativedelta import relativedelta
from oauth2client.client import GoogleCredentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from Crypto.Cipher import AES

date_current = datetime.datetime.now() + relativedelta(months=1)
date_current = round(date_current.timestamp())
date_L30D = datetime.datetime.now()+ relativedelta(months=-1)
date_L30D = round(date_L30D.timestamp())

def get_keyword(url, sheet_name, location):
  auth.authenticate_user()
  gc = gspread.authorize(GoogleCredentials.get_application_default())
  wb = gc.open_by_url(url)
  worksheet = wb.worksheet(sheet_name)
  key_word_list = worksheet.col_values(location)
  return key_word_list

def get_API_access_token():

    AES_BLOCK_SIZE = 16
    AES_CBC_IV = '\0' * AES_BLOCK_SIZE


    def pkcs7_padding(data, block_size):
        pad = block_size - (len(data) % block_size)
        data += chr(pad) * pad
        return data


    def aes_cbc_encrypt(data, key):
        return AES.new(key, AES.MODE_CBC, AES_CBC_IV).encrypt(data)

    def encrypt_password(raw_password, salt, verify_code, raw_key_password=None):
        if raw_key_password is None:
            raw_key_password = raw_password
        encryption_key = hashlib.sha256(hashlib.sha1(
            (raw_key_password + salt).encode('utf-8')
        ).hexdigest().lower().encode('utf-8') + verify_code.encode('utf-8')).digest()

        encrypted_password = aes_cbc_encrypt(pkcs7_padding(raw_password, AES_BLOCK_SIZE), encryption_key)
        encrypted_password = encrypted_password.hex().lower()
        return encrypted_password

    access_token = ""


    def request_api(url, data, method="POST", format="JSON"):
        print("\n+ REQUEST:", url)
        headers = {
            "X-App-Type": "xx",
            "X-Api-Version": "xx",
            "X-Client-Type": "xx",
            "X-Client-Version": "xx",
            "X-Client-Id": "xx",
            "X-Access-Token": access_token,
        }
        if method == "POST":
            if format == "JSON":
                response = requests.post(url, data=json.dumps(data), verify=False, headers=headers)
            else:
                multipart_data = {}
                for key, value in data.iteritems():
                    multipart_data[key] = (None, value)
                print(multipart_data)
                response = requests.post(url, files=multipart_data, verify=False, headers=headers)
        else:
            response = requests.get(url, params=data, verify=False, headers=headers)
        try:
            if response.status_code != 200:
                print("  REQUEST HTTP ERROR CODE: %s" % response.status_code)
                return None, None
            result = response.json()
            result_code = result["result"]
            result_body = result.get("reply")
            return result_code, result_body
        except Exception as error:
            print("  REQUEST EXCEPTION: %s" % error.message)
        return None, None


    def get_access_token(account, password):
        try:
            result_code, prelogin = request_api("https://xx.xx", {"account": account})
            verify_code = prelogin["verify_code"]
            salt = prelogin["salt"]

            encrypted_password = encrypt_password(password, salt, verify_code)
            result_code, login = request_api("https://xx.xx",
                                             {"account": account, "password": encrypted_password})

            return login["access_token"]
        except:
            error = traceback.format_exc()
            print(error)
            return None


    # config here
    def get_username_pwd():
      #replace information bellow by your info
        dictionary = {"username":"xx","pwd":"xx","pwd_api":"xx","pwd_db_crm":"xx"}
        username = dictionary['username']
        pwd = dictionary['pwd']
        pwd_api = dictionary['pwd_api']
        pwd_crm = dictionary['pwd_db_crm']

        return username, pwd, pwd_api, pwd_crm


    username, pwd, pwd_api, pwd_crm = get_username_pwd()

    TEST_ACCOUNT = username
    TEST_PASSWORD = pwd_api


    access_token = get_access_token(TEST_ACCOUNT, TEST_PASSWORD)
    # print(access_token)

    return access_token

#------------------------------------------------------------------------------------------------------
# get all_request id
url = 'https://xx.xx'
myobj = {"status" : 10}
myobj = json.dumps(myobj)
token = get_API_access_token()
headers={"X-App-Type": "xx",
            "X-Api-Version": "xx",
            "X-Client-Type": "xx",
            "X-Client-Version": "xx",
            "X-Client-Id": "xx",
            'X-Access-Token':token
            }
x = requests.post(url, data = myobj, headers = headers)
res = json.loads(x.content)

#get all merchant base on request_id
size = len(res['reply']['registration_ids'])
reg_list = res['reply']['registration_ids']
no_bin = math.ceil(size/2000)
page_limit = 2000
final_list = []
for i in range(no_bin):
  tmplist=[reg_list[i*2000+n] for n in range(page_limit) if (i*2000+n) < size]
  my_dict = {"registration_ids":tmplist}
  url_info = 'https://xx.xx'
  myobj_info = json.dumps(my_dict)
  x_info = requests.post(url_info, data = myobj_info, headers = headers)
  res_info = json.loads(x_info.content)
  final_list.extend(res_info['reply']['registrations'])

df = pd.DataFrame(final_list)

def convert_time(row, cl_name):
  try:
    out = datetime.datetime.fromtimestamp(row[cl_name] + 3600*7)
  except:
    out = ''
  return out

# df.head()
columns = ['id', 'update_time',  'status', 'restaurant_basic_info', 'representative_info', 'welcome_package', 'nmw_info', 'approved_restaurant_id']
df = df[columns]
df1 = df.restaurant_basic_info.apply(pd.Series)
df2 = df.representative_info.apply(pd.Series)
df3 = df.welcome_package.apply(pd.Series)
df['update_time'] = df.apply(lambda x: convert_time(x, 'update_time'), axis = 1) 
df['mex_name'] = df1['name']
df['email'] = df2['email']
df['phone'] = df2['phone_number']
df['name'] = df2['full_name']

status = {2: 'waiting_BD',
          1: 'Draft',
          3: 'Cancel',
          4: 'Reject',
          10: 'success',
          9: 'fail'}

df.status = np.where(df.status.isin(status), df.status.map(status), 'process')
df['contract_type'] = df['nmw_info'].notnull().astype(int)
contract_type = {1: "contract&nmw", 0:"contract only"}
df['contract_type'] = df['contract_type'].map(contract_type)
x = datetime.datetime(2021, 3, 1)
columns = ['approved_restaurant_id', 'mex_name', 'id', 'update_time', 'name', 'phone', 'email', 'contract_type', 'nmw_info', 'status']
df = df[columns]
df = df[df['update_time'] >= x]
df['approved_restaurant_id'] = df['approved_restaurant_id'].astype(int)

# sended_mex = get_keyword('https://docs.google.com/spreadsheets/d/1nidmfHjNgH2cWBXjYwZB_Y39k_iUSGxN4RUJv9G7bLo/edit#gid=11005675', 'Tracker', 5)[3:]
# sended_mex = [int(i) for i in sended_mex]
# df = df[~df['approved_restaurant_id'].isin(sended_mex)]


auth.authenticate_user()
gc = gspread.authorize(GoogleCredentials.get_application_default())

wb = gc.open_by_url('https://docs.google.com/spreadsheets/d/1-PJx0J-m27IKvBQOf0xf4rA-z38VKEPyXXJXNIYQDwA/edit?usp=sharing')
worksheet = wb.worksheet("raw")
wb.values_clear("Raw!A1:L100000")
set_with_dataframe(worksheet, df)