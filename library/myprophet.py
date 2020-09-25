import fbprophet as fb
from library import broker as td
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_log_error
from sklearn.metrics import median_absolute_error


class Prophesy(object):
    """Wrapper of Facebook Prophet for time-series price modeling."""
    def __init__(self, tick, years, split_date):
        self.ticker = td.get_price_hist(str(tick), "daily", 1, "year", years)
        data = pd.concat([self.ticker.datetime.dt.date, self.ticker.close], axis = 1).dropna()
        self.data = data.rename(columns = {'datetime':'ds', 'close':'y'})
        self.training = self.data[pd.to_datetime(self.data.ds) <= pd.to_datetime(str(split_date))]
        self.testing = self.data[pd.to_datetime(self.data.ds) > pd.to_datetime(str(split_date))]
        self.testing = self.testing.set_index('ds')
        self.testing.index = pd.to_datetime(self.testing.index)
        self.training = self.training.set_index('ds')
        self.training.index = pd.to_datetime(self.training.index)
        self.predict_period = len(self.testing)

    def gen_forecast(self, cycle, fourier=8, weekly_seasonality = True, yearly_seasonality=True,
                     daily_seasonality=False, int_width=0.8, chngpt_scale=.05, chngpts=None):

        self.model = fb.Prophet(weekly_seasonality=weekly_seasonality
                                , yearly_seasonality=yearly_seasonality, daily_seasonality=daily_seasonality
                                , interval_width= int_width,
                                changepoint_prior_scale = chngpt_scale, changepoints=chngpts)
        self.model.add_seasonality('self_define_cycle', period=cycle, fourier_order=fourier)
        self.model.fit(self.data)
        self.future = self.model.make_future_dataframe(periods=self.predict_period)
        self.fcast = self.model.predict(self.future)


    def forecast_plot(self):
        self.model.plot(self.fcast)
        plt.plot(self.testing.index, self.testing.values, '.', color='#ff3333', alpha=0.6)
        plt.xlabel('Date', fontsize=12, fontweight='bold', color='gray')
        plt.ylabel('Price', fontsize=12, fontweight='bold', color='gray')
        plt.show()

    def forecast_returns(self):
        self.ret = max(self.fcast.self_define_cycle) - min(self.fcast.self_define_cycle)
        self.model_df = self.fcast['yhat']
        self.model_df.index = self.fcast['ds'].map(lambda x: x.strftime("%Y-%m-%d"))
        self.out_df = pd.concat([self.testing, self.model_df], axis=1)
        self.out_df = self.out_df[~self.out_df.iloc[:, 0].isnull()]
        self.out_df = self.out_df[~self.out_df.iloc[:, 1].isnull()]
        self.mse = mean_squared_error(self.out_df.iloc[:, 0], self.out_df.iloc[:, 1])
        self.mae = mean_absolute_error(self.out_df.iloc[:, 0], self.out_df.iloc[:, 1])
        self.r2 = r2_score(self.out_df.iloc[:, 0], self.out_df.iloc[:, 1])
        self.mslog = mean_squared_log_error(self.out_df.iloc[:, 0], self.out_df.iloc[:, 1])
        self.mae = median_absolute_error(self.out_df.iloc[:, 0], self.out_df.iloc[:, 1])

        rep = [self.ret, self.mse, self.mae, self.r2, self.mslog, self.mae]
        print("Projected return per cycle: {}".format(round(rep[0], 2)))
        print("MSE:  {}".format(round(rep[1], 4)))
        print("MAE:  {}".format(round(rep[2], 4)))
        print("R2:   {}".format(round(rep[3], 4)))
        print("MSLE: {}".format(round(rep[4], 4)))
        print("MAE:  {}".format(round(rep[5], 4)))

