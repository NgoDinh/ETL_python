import os
import ast
import time
import gspread
import datetime
import traceback
import pandas as pd
from imbox import Imbox # pip install imbox
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

file = open("info.txt", "r")
contents = file.read()
dictionary = ast.literal_eval(contents)
file.close()

host = dictionary['host']
username = dictionary['username']
password = dictionary['pass']
download_folder = "."
    
mail = Imbox(host, username=username, password=password, ssl=True, ssl_context=None, starttls=False)
messages = mail.messages(date__gt=datetime.date.today()) #datetime.date.today()
#  subject='log_flow_auto'
for (uid, message) in messages:
    for idx, attachment in enumerate(message.attachments):
        att_fn = attachment.get('filename')
        if 'xlsx.gpg' in att_fn:
            download_path = f"{download_folder}/{att_fn}"
            print(download_path)
            with open(download_path, "wb") as fp:
                fp.write(attachment.get('content').read())
            print(traceback.print_exc())

mail.logout()
print(att_fn)
os.system('gpg1 -o {op} -d --passphrase xxx {ip}'.format(ip=att_fn,op='auto_list_volumn.xlsx'))
time.sleep(3)
df = pd.read_excel('xxx.xlsx')
os.system('rm {ip}'.format(ip=att_fn))
os.system('rm {ip}'.format(ip='xxx.xlsx'))

creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json')
client = gspread.authorize(creds)
ss = client.open_by_key('client_key')
title_cc = "cc_" + att_fn.split(".")[0]
title_cl = "cl_" + att_fn.split(".")[0]
ss.add_worksheet(title=title_cc,rows="100", cols="20")
ss.add_worksheet(title=title_cl,rows="100", cols="20")

df_cc = df[df.prod_type=="CC"]
df_cc = df_cc[df_cc.rrank_range != 'rank[31-100]']
df_cc = df_cc.drop("pct_allowed", axis=1)

df_cl = df[df.prod_type=="CL"]
df_cl = df_cl[(df_cl.cs_range != "(300-599)_Error")&(df_cl.rrank_range != 'rank[31-100]')]
df_cl = df_cl.drop("pct_allowed", axis=1)

s_cc = ss.worksheet(title_cc)
set_with_dataframe(s_cc, df_cc) 

s_cl = ss.worksheet(title_cl)
set_with_dataframe(s_cl, df_cl) 