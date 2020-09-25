"""
Static Library of Functions to wrap Pyfolio Backtesting to interact with AMTDpy portfolio and prices.
"""

from library import broker as td
import pyfolio as pyf
import pandas as pd
import numpy as np
import time
import datetime as dt
from datetime import timedelta

#example sector map
"""sect_map = {'AAPL': 'Technology',
            'AMTD': 'Financials', 
            'BA': 'Industrials', 
            'GPRO': 'Technology',
            'QQQ': 'Technology', 
            'ROBO': 'Technology', 
            'SPY': 'Market',
            'TLRY':'MJ', 'VZ':'Communications', 'WMT':"Consumer Discretionary"
           }"""



###LIST OF TRANSACTIONS EXCEL FILE
trns = pd.read_csv('pyfolio_example - transactions.csv')
trns.nxt_txn[trns.nxt_txn.isna()] = dt.datetime.today().strftime('%Y-%m-%d')

def getclosingPs(ticklist, yrs, close):
    prices = {}
    ps = pd.DataFrame(pd.date_range(start=dt.datetime.today() - timedelta(days=yrs * 365),
                                    end=dt.datetime.today().strftime('%Y-%m-%d')))
    ps = ps.rename(columns={0: 'date'})
    # ps['date'].strftime('%Y-%m-%d')
    ps = ps.set_index('date', drop=True)
    ps.index = ps.index.strftime('%Y-%m-%d')

    for i in ticklist:
        time.sleep(1)
        prices[i] = td.get_price_hist(i, "daily", 1, "year", yrs)
        prices[i] = prices[i].set_index(list(prices[i].filter(like='datetime')))
        prices[i].index = prices[i].index.strftime('%Y-%m-%d')
        prices[i].columns = prices[i].columns + '_' + str(i)
        ps = pd.concat([ps, prices[i]], axis=1)

    if bool(close) == True:
        close = ps.filter(like='close')
        close.columns = close.columns.str.replace('close_','')
        close = close.reindex(sorted(close.columns), axis=1)
        return close
    else:
        return ps



#create portfolio dataframe
def build_pf_df(trns, starting_cash):
    start_dt = pd.to_datetime(trns.txn_dt[0]) - timedelta(days=1)
    pf = pd.DataFrame(pd.date_range(start=start_dt , end=dt.datetime.today().strftime('%Y-%m-%d')))
    pf = pf.rename(columns = {0:'date'})

    for i in trns.symbol.unique():
        pf[str(i)] = 0
    pf['cash'] = starting_cash

    for i in trns.index:
        row = trns.iloc[i]
        prev_amt = pf[str(row.symbol)][(pf.date == (pd.to_datetime(row.txn_dt) - timedelta(days=1)))].item()
        pf[str(row.symbol)][(pf.date >= row.txn_dt) & (pf.date <= row.nxt_txn)] = prev_amt + row.amount
        pf['cash'][(pf.date >= row.txn_dt) & (pf.date <= row.nxt_txn)] = row.cash
    pf = pf.reindex(sorted(pf.columns), axis=1)
    pf = pf.set_index('date',drop=True)
    return pf

def build_pos_df(pf, close, cash):
    pf = pf.drop(columns ='cash')
    pos = pd.DataFrame(pf * close).dropna(axis='rows', how='all').fillna(0)
    pos = pos.join(cash, how='left')
    pos.index = pos.index.rename('index')
    pos.index = pos.index.tz_localize('UTC')
    return pos

def calc_log_ret(pos):
    myret = pos.sum(axis=1)
    logret = np.log(myret / myret.shift(1))
    return logret

def build_trxn_df(trns, pos):
    trns = trns.set_index('txn_dt',drop=True)
    trns['sid'] = 0
    mytxn= trns[['amount','price','sid','symbol','txn_dollars']]
    for i in range(0, len(pos.columns)):
        symb = pos.columns[i]
        mytxn['sid'][mytxn['symbol'] == symb] = i
    mytxn.index = pd.to_datetime(mytxn.index).strftime('%Y-%m-%d').astype('<M8[ns]')
    mytxn.index = mytxn.index.tz_localize('UTC')
    return mytxn


def build_trxns_from_buy_sell_df(trans, close, starting_cash):
    txn = {}
    my_txns = pd.DataFrame(columns=['amount', 'price', 'symbol', 'txn_dollars'])
    for i in trans.columns:
        txn[i] = pd.DataFrame(trans[i][trans[i] != 0])
        txn[i] = txn[i].rename(columns={str(i): 'amount'})

        txn[i]['symbol'] = str(i)
        txn[i] = pd.merge(pd.DataFrame(close[i]), txn[i], how='inner', left_on=close.index, right_on=txn[i].index)
        txn[i] = txn[i].rename(columns={str(i): 'price', 'key_0': 'txn_dt'})
        txn[i]['txn_dollars'] = - txn[i]['price'] * txn[i]['amount']  ## negative price amount being bought
        txn[i]['nxt_txn'] = txn[i]['txn_dt'].shift(-1)
        my_txns = pd.concat([my_txns, txn[i]], axis=0)
    my_txns = my_txns.sort_values(by='txn_dt').set_index('txn_dt', drop=True)
    my_txns['cum_txn'] = my_txns.txn_dollars.cumsum()
    my_txns = my_txns.fillna(dt.datetime.today().strftime('%Y-%m-%d'))
    my_txns['cash'] = starting_cash + my_txns.cum_txn  ###used to be minus
    trxns = my_txns.reset_index()[['symbol', 'txn_dt', 'nxt_txn', 'amount', 'price', 'txn_dollars', 'cash']]
    return trxns


def ticker_map(trans):
    keys = trans.symbol.unique()
    values = trans.symbol.unique()
    sect_map = dict(zip(keys, values))
    return sect_map

#pyf.create_position_tear_sheet(returns, pos, sector_mappings=sect_map)
def full_tear_sheet(returns, positions, transactions, oos_date, sect_map):
    ret = returns
    pos = positions
    txn = transactions
    #ret.index = ret.index.tz_localize('UTC')
    #pos.index = pos.index.tz_localize('UTC')
    #txn.index = txn.index.tz_localize('UTC')
    oos_date = (oos_date)

    return pyf.create_full_tear_sheet(ret,
                          positions=pos,
                          transactions=txn,
                          live_start_date=oos_date,
                          slippage=0.0,
                          sector_mappings=sect_map)



def position_tear_sheet(returns, positions, sect_map):
    ret = returns
    pos = positions
    #pos.index = pos.index.tz_localize('UTC')
    #ret.index = ret.index.tz_localize('UTC')
    return pyf.create_position_tear_sheet(ret, pos, sector_mappings=sect_map)


def returns_tear_sheet(returns):
    ret = returns

    #pos.index = pos.index.tz_localize('UTC')
    #ret.index = ret.index.tz_localize('UTC')
    return pyf.create_returns_tear_sheet(ret)


def roundtrip_tear_sheet(returns, positions, transactions, sect_map):
    ret = returns
    pos = positions
    txn = transactions
    ret.index = ret.index.astype('<M8[ns]')
    pos.index = pos.index.astype('<M8[ns]')
    txn.index = txn.index.astype('<M8[ns]')
    pyf.create_round_trip_tear_sheet(ret, pos, txn, sector_mappings=sect_map)
    return

