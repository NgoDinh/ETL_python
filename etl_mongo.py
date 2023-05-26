import json
import datetime
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from pymongo import MongoClient
from google.cloud import bigquery
from bson import json_util, ObjectId

#connect to Mongodb
connection_string = json.load(open("mongo_info.json"))["link"]

def get_data(input_db_name, input_cl_name, backup_day=1, cl_name_adjust = None, more_filter = None, cd_adjust = None):
    client = MongoClient(connection_string)
    db = client[input_db_name]
    cl = db.get_collection(input_cl_name)

    #filter data
    for xday in range(backup_day):
        end = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = end - datetime.timedelta(days=(xday))
        start = end - datetime.timedelta(days=1)
    #    start = end - datetime.timedelta(days=(xday+2))
        date_string = start.strftime("%Y%m%d")
        qr = {
            "createdAt":{
                    '$gte':start,
                    '$lt':end
                    }
            }
        if cd_adjust != None:
            qr[cd_adjust] = qr.pop("createdAt")
        if more_filter != None:
            qr.update(more_filter)
        data = cl.find(qr)
        data = [i for i in data]
        data = json.loads(json_util.dumps(data))
        for i in data:
            for key in i.keys():
                i[key] = str(i[key])
                
        #define table name        
        prefix = 'taptap-c2c5f.manual_dwh.ram_'
        if cl_name_adjust == None:
            table_id = prefix + input_db_name + "__" + input_cl_name + "_" + date_string
        else:
            table_id = prefix + input_db_name + "__" + cl_name_adjust + "_" + date_string
            
        if len(data)>0:
            #convert to the same size
            df1 = pd.DataFrame.from_records(data)
            data = []
            for i in range(len(df1)):
                data.append(json.loads(df1.iloc[i, :].to_json()))
            
            #find schema
            schema = []
            new_col_name = []
            for name in data[0].keys():
                new_col_name.append("_".join(name.split(" ")))
                schema.append(bigquery.SchemaField("_".join(name.split(" ")), bigquery.enums.SqlTypeNames.STRING))

            #connect to bigquery
            client = bigquery.Client.from_service_account_json('google_token.json')
            job_config = bigquery.LoadJobConfig(
                schema=schema,
                write_disposition="WRITE_TRUNCATE",
            )
            print(table_id)
            status = "success"
            try:
                job = client.load_table_from_json(
                    data, table_id, job_config=job_config
                )
                print(job.result())
            except:
                status = "fail"
            #update status
            rows_to_insert = [{"table_id": table_id, "no_row": str(len(data)), "status": status, "time":str(datetime.datetime.now())}]
            table_controller = client.get_table("{}.{}.{}".format("taptap-c2c5f", "manual_dwh", "controller"))    
            client.insert_rows_json(table_controller, rows_to_insert)
        else:
            client = bigquery.Client.from_service_account_json('google_token.json')
            rows_to_insert = [{"table_id": table_id, "no_row": str(0), "status": "no_data", "time":str(datetime.datetime.now())}]
            table_controller = client.get_table("{}.{}.{}".format("taptap-c2c5f", "manual_dwh", "controller"))    
            client.insert_rows_json(table_controller, rows_to_insert)