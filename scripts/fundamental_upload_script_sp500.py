"""
Script for uploading SP500 Fundamental Data to the Local DB.
"""

from library import DBA as db, broker as td
import pandas as pd
import time
import logging
import datetime


logger = logging.getLogger('fundamental_application')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('C:/Users/bheim/PythonProjects/bat_files/logs/SP500_fundamentals_{}.log'.format(time.strftime("%Y%m%d")))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.debug('Starting SP500 Fundamental Program {}'.format(datetime.datetime.now()))


all_ticks = db.get_sp500()
all_ticks = all_ticks.rename(columns = {0:'symb'})
logger.debug('Successfully queried SP500 ticks {}'.format(datetime.datetime.now()))

#create table -- do not upload data
#data = td.get_fundamentals('AAPL')
#db.create_postgres_table(data, "td_fundamentals") #need to edit dtypes after
print('Beginning to Call TDA API')
##start getting prices and upload to DB, 500 takes about 10 minutes - may take up to 40 or an hour for 2k
success = []
fail = []

A = pd.DataFrame()
for i in (all_ticks.symb):
    time.sleep(1)           #max two api calls per second
    try:
        newdata =td.get_fundamentals(str(i))
        A = pd.concat([A, newdata], axis = 0, sort =True)
        success.append(str(i))
    except:
        print(str(i)+" failed.")
        fail.append(str(i))
        logger.debug('{} failed.'.format(str(i)))
        pass
    if (len(success) + len(fail)) % 100 == 0:
        print((len(success) + len(fail)) / len(all_ticks.symb))
    else:
        continue
logger.debug('Finished creating dataframe of fundamental data {}'.format(datetime.datetime.now()))
logger.debug('Failed Ticks: {}'.format(str(len(fail))))
logger.debug('Successful Ticks: {}'.format(str(len(success))))

db.data_upload_pg(A, "td_fundamentals")
logger.debug('Finished uploading data to table {}'.format(datetime.datetime.now()))
#####
pd.Series(fail).to_csv('fundamentals_fail.csv')
pd.Series(success).to_csv('fundamentals_success.csv')
