"""
Static functions for high level sector fundamental analysis and equity clustering using local DB.
"""

from library import DBA as db, blakefolio as bf
import pandas as pd
import matplotlib.pyplot as plt


def get_sp500_sectors():
    sql = """select  symbol, sector  from sp500"""
    sectors = db.query_db(sql)
    sectors = sectors.rename(columns={0: 'symbol', 1: 'sector'})
    return sectors

def get_latest_fundamentals():
    sql1 = """select max(update_ts) from public.td_fundamentals"""
    maxdate = db.query_db(sql1)
    maxdt = pd.to_datetime(maxdate.values.item())
    maxdt = maxdt.strftime("%Y-%m-%d")
    sql2 = """select * from public.td_fundamentals where date(update_ts) = '{}'""".format(str((maxdt)))
    fundamentals = db.query_db(sql2)
    fundamentals = fundamentals.rename(
        columns={0: 'indicator', 1: 'value', 2: 'update_ts', 3: 'asset_type', 4: 'cusip', 5: 'symbol', 6: 'id'})
    return fundamentals

def create_fundamental_df(fundamentals, sectors):
    fund_df = fundamentals[['symbol', 'indicator', 'value']]
    d = {}
    test = pd.DataFrame()
    for i in fund_df.symbol.unique():
        d[i] = fund_df[['indicator', 'value']][fund_df.symbol == str(i)].T
        d[i] = d[i].rename(columns=d[i].iloc[0]).drop(d[i].index[0]).reset_index(drop=True)
        d[i]['Symbol'] = str(i)
        try:
            test = pd.concat([d[i], test], axis=0, sort=True).reset_index(drop=True)
        except:
            print(str(i) + " failed.")
            pass
    Fs = test.merge(sectors, left_on='Symbol', right_on='symbol').drop(columns='Symbol')
    Fs = Fs.apply(pd.to_numeric, downcast='float', errors='ignore')
    return Fs


def run_hist_analysis(Fs_df, sector, list_of_indicators, alpha):
    for i in list_of_indicators:
        plt.title(str(i))
        Fs_df[str(i)][Fs_df.sector == str(sector)].hist()
        plt.axvline(Fs_df[str(i)].mean(), color='k', linestyle='dashed', linewidth=1)
        plt.show()
        print(">90 PERCENTILE")
        print(Fs_df.symbol[(Fs_df[str(i)] > Fs_df[str(i)].quantile(1-alpha)) & (Fs_df.sector == str(sector))])
        print("<10 PERCENTILE")
        print(Fs_df.symbol[(Fs_df[str(i)] < Fs_df[str(i)].quantile(alpha)) & (Fs_df.sector == str(sector))])

def get_annual_returns(list_of_symbols):
    close = bf.get_closeP_df(list_of_symbols)
    returns_daily = close.pct_change()
    returns_annual = returns_daily.mean() * 250
    return returns_annual

def get_ratios_returns_df(Fs_df, sector):
    fin_ratios = Fs_df[Fs_df.sector == str(sector)].set_index('symbol')
    ann_ret = get_annual_returns(fin_ratios.symbol.unique())
    fin_ratios_returns = pd.concat([fin_ratios, ann_ret], axis=1)
    fin_ratios_returns = fin_ratios_returns.rename(columns={0: 'ann_ret'})
    return fin_ratios_returns

import pydotplus
from IPython.display import Image
from sklearn import tree
from sklearn.tree import DecisionTreeClassifier

def returns_classification_analysis(fin_ratios_returns, n_cuts):
    returns = pd.DataFrame(fin_ratios_returns['ann_ret'])
    returns['ret_cat'] = pd.cut(returns['ann_ret'], n_cuts)
    Y = returns['ret_cat'].astype(str)
    X = fin_ratios_returns.drop(columns = ['ann_ret','sector'], axis = 1)
    clf = DecisionTreeClassifier(random_state=0)
    model = clf.fit(X,Y)
    dot_data = tree.export_graphviz(clf, out_file=None,
                                    feature_names=X.columns,
                                    class_names=returns['ret_cat'].astype(str).unique())
    # Draw graph
    graph = pydotplus.graph_from_dot_data(dot_data)
    # Show graph
    Image(graph.create_png())
    graph.write_png("tree.png")
    return pd.concat([fin_ratios_returns, Y], axis = 1)



