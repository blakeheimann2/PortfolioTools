"""Static database access functions for interacting with local database"""

import pandas as pd
import psycopg2
from io import StringIO
import config as cf

def query_db(query):
    connection = psycopg2.connect(user=cf.DBuser,
                              password=cf.DBpass,
                              host=cf.DBhost,
                              port=cf.DBport,
                              database="mydb")
    cursor = connection.cursor()
    cursor.execute(query)
    data = cursor.fetchall()   #to create a table etc. use connection.commit() instead of this line
    data = pd.DataFrame(data)
    cursor.close()
    connection.close()
    return data

def get_sp500():
    connection = psycopg2.connect(user=cf.DBuser,
                              password=cf.DBpass,
                              host=cf.DBhost,
                              port=cf.DBport,
                              database="mydb")
    cursor = connection.cursor()
    query = '''select * from sp500'''
    cursor.execute(query)
    sp500 = cursor.fetchall()   #to create a table etc. use connection.commit() instead of this line
    sp500 = pd.DataFrame(sp500)
    cursor.close()
    connection.close()
    return sp500

def get_all_ticks():
    connection = psycopg2.connect(user=cf.DBuser,
                              password=cf.DBpass,
                              host=cf.DBhost,
                              port=cf.DBport,
                              database="mydb")
    cursor = connection.cursor()
    query = '''select distinct symbol from public."fundamentals_Q2_2019"'''
    cursor.execute(query)
    ticks = cursor.fetchall()   #to create a table etc. use connection.commit() instead of this line
    ticks = pd.DataFrame(ticks)
    cursor.close()
    connection.close()
    return ticks


def create_postgres_table(data, tablename):
    query = """CREATE TABLE public.%tablename% (%newcolumns% id varchar NULL );"""
    newcols = []
    for i in data.columns:
        string = i + " varchar NULL,"
        newcols.append(string)
    cols = ' '.join(newcols)
    q2 = query.replace('%tablename%', tablename)
    q2 = q2.replace('%newcolumns%', cols)
    conn = psycopg2.connect(user=cf.DBuser,
                              password=cf.DBpass,
                              host=cf.DBhost,
                              port=cf.DBport,
                              database="mydb")
    with conn.cursor() as c:
        c.execute(q2)
        conn.commit()
        conn.close()


def data_upload_pg(data, table):
    data['id'] = data.reset_index().index
    data = data.replace(',','')#need to do this to
    conn = psycopg2.connect(user=cf.DBuser,
                              password=cf.DBpass,
                              host=cf.DBhost,
                              port=cf.DBport,
                              database="mydb")

    sio = StringIO()
    sio.write(data.to_csv(index=None, header=None))  # Write the Pandas DataFrame as a csv to the buffer
    sio.seek(0)

    with conn.cursor() as c:
        c.copy_from(sio, table, columns=data.columns, sep=',')
        conn.commit()
        conn.close()











