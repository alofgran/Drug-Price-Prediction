import pandas as pd
import numpy as np
import datetime as dt

import matplotlib.pyplot as plt

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Select, DataRange1d, HoverTool
from bokeh.plotting import figure

import dill

from sklearn import base
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression

#Import data
Price_Patent_Reg = dill.load(open('data/features_created.pkd', 'rb'))
Price_Patent_Reg = pd.get_dummies(Price_Patent_Reg, drop_first = True).copy()

#Train-test split data
train_data, test_data = train_test_split(Price_Patent_Reg,
                                         test_size = 0.2,
                                         random_state = 1,
#                                          shuffle = True
                                        )    #shuffle data to avoid correlation to the natural order of the data

class GroupbyEstimator(base.BaseEstimator, base.RegressorMixin):


    def __init__(self, groupby_column, pipeline_factory):
        # column is the value to group by; estimator_factory can be called to produce estimators
        self.groupby_column = groupby_column
        self.pipeline_factory = pipeline_factory


    def fit(self, dataframe, label):
        # Create an estimator and fit it with the portion in each group (create and fit a model per city
        self.drugs_dict = {}
        self.label = label
        self.coefs_dict = {}
        self.intercepts_dict = {}

        dataframe = pd.get_dummies(dataframe)  #onehot encoder had problems with the data, so I'm getting the dummies with pandas here

        for name, values in dataframe.groupby(self.groupby_column):
            y = values[label]
            X = values.drop(columns = [label, self.groupby_column], axis = 1)
            self.drugs_dict[name] = self.pipeline_factory().fit(X, y)
            self.coefs_dict[name] = self.drugs_dict[name].named_steps["lin_reg"].coef_
            self.intercepts_dict[name] = self.drugs_dict[name].named_steps["lin_reg"].intercept_
        return self

    #Method to get the coefficients for each regression
    def get_coefs(self):
        return self.coefs_dict

    #Method to get the intercepts for each regression
    def get_intercepts(self):
        return self.intercepts_dict


    def predict(self, test_data):
        price_pred_list = []

        for idx, row in test_data.iterrows():
            name = row[self.groupby_column]                                 #get drug name from drug column
            regression_coefs = self.drugs_dict[name]                        #get coefficients from fitting in drugs_dict
            row = pd.DataFrame(row).T
            X = row.drop(columns = [self.label, self.groupby_column], axis = 1).values.reshape(1, -1) #Drop ndc and price cols

            drug_price_pred = regression_coefs.predict(X)
            price_pred_list.append([name, drug_price_pred])
        return price_pred_list

def pipeline_factory():
    return Pipeline([
                     ('lin_reg', LinearRegression())
                    ])

lin_model = GroupbyEstimator('ndc', pipeline_factory).fit(train_data,'nadac_per_unit')

# Prep data for plotting (from training/testing data)
def format_data(dataframe, filename, test = False):#########
    #change columns to datetime
    dataframe.loc[:, 'ndc'] = dataframe.loc[:, 'ndc'].astype('int64') #int64 needed due to size of numbers
    if test:
        dataframe.loc[:, ['effective_date_year', 'effective_date_month', 'effective_date_day']] = dataframe.loc[:, ['effective_date_year', 'effective_date_month', 'effective_date_day']].astype(str)
        dataframe.rename(columns = {'effective_date_year': 'year', 'effective_date_month': 'month', 'effective_date_day': 'day'}, inplace = True)
        dataframe.loc[:, 'date'] = pd.to_datetime(dataframe[['year', 'month', 'day']], format = '%Y-%m-%d')
        dataframe.rename({'year': 'effective_date_year', 'month': 'effective_date_month', 'day': 'effective_date_day'}, inplace = True)
        dataframe.loc[:, ['year', 'month', 'day']] = dataframe.loc[:, ['year', 'month', 'day']].astype(float).astype(int)
        dataframe.sort_values(['ndc', 'date'])
    else:
        dataframe.rename(columns = {'effective_date_year': 'year', 'effective_date_month': 'month', 'effective_date_day': 'day'}, inplace = True)
    #Keep only unique values
    dataframe.loc[:, 'year'] = dataframe.loc[:, 'year'].astype(int)
    dataframe.loc[:, 'month'] = dataframe.loc[:, 'month'].astype(int)
    dataframe.loc[:, 'day'] = dataframe.loc[:, 'day'].astype(int)
    dataframe.loc[:, 'nadac_per_unit'] = dataframe.loc[:, 'nadac_per_unit'].astype('float16')
    return dataframe

#Save formatted data as follows
historical_data = format_data(train_data, 'historical_data', test = True).copy()
prediction_data = format_data(test_data, 'pred_data').copy()

# historical_data = historical_data.drop('date', axis=1)

#Plotting session
# Set up initial data
historical_data = historical_data.loc[:, ['ndc', 'date', 'nadac_per_unit']]
hist_temp = historical_data[historical_data.loc[:, 'ndc']==781593600].sort_values('date')
historical_source = ColumnDataSource(data = hist_temp)


#Get initial prediction
date = dt.datetime.strptime('-'.join(('2020', '3', '31')), '%Y-%m-%d')
new_prediction_data = prediction_data[prediction_data.loc[:, 'ndc']==781593600] #working
new_prediction_data.loc[:, 'year'] = date.year
new_prediction_data.loc[:, 'month'] = date.month
new_prediction_data.loc[:, 'day'] = date.day
new_prediction_data = lin_model.predict(new_prediction_data)
new_prediction_data = pd.DataFrame(data = {'ndc':new_prediction_data[0][0], 'nadac_per_unit':new_prediction_data[0][1][0]}, index = [0]) #these element slices are correct
new_prediction_data['date'] = pd.to_datetime(date, format='%Y-%m-%d')
new_prediction_data['ndc'] = new_prediction_data['ndc'].astype(float).astype('int64')
new_prediction_data['nadac_per_unit'] = new_prediction_data['nadac_per_unit'].astype('float16')
prediction_source = ColumnDataSource(data=new_prediction_data)

id_list = list(prediction_data['ndc'].astype(str))
# Set up plot
plot = figure(plot_height=800, plot_width=800, title='Drug Price Over Time',
              x_axis_type = 'datetime',
              tools="crosshair, pan, reset, save, wheel_zoom")
plot.xaxis.axis_label = 'Time'
plot.yaxis.axis_label = 'Price ($)'
plot.axis.axis_label_text_font_style = 'bold'
plot.grid.grid_line_alpha = 0.8
plot.title.text_font_size = '16pt'
plot.x_range = DataRange1d(range_padding = .01)
plot.add_tools(HoverTool(tooltips=[('Date', '@date{%F}'), ('Price', '@nadac_per_unit')],
                                    formatters = {'date': 'datetime'}))

plot.line('date', 'nadac_per_unit', source=historical_source, legend_label='Historical Price')
plot.scatter('date', 'nadac_per_unit', source=prediction_source, fill_color='red', size=8, legend_label='Predicted Price')

# Set up widgets
id_select = Select(title='Select a Drug ID Number', value='781593600', options=id_list)

# Set up callbacks
def update_data(attrname, old, new):

    #Get the current select value
    curr_id = id_select.value
    # Generate the new data
    new_historical = historical_data[historical_data.loc[:, 'ndc']==int(curr_id)]
    new_historical = new_historical.sort_values('date')

    new_prediction_data = prediction_data[prediction_data.loc[:, 'ndc']==int(curr_id)] #working
    date = dt.datetime.strptime('-'.join(('2020', '3', '31')), '%Y-%m-%d')
    new_prediction_data.loc[:, 'year'] = date.year
    new_prediction_data.loc[:, 'month'] = date.month
    new_prediction_data.loc[:, 'day'] = date.day
    new_prediction_data = lin_model.predict(new_prediction_data)
    new_prediction_data = pd.DataFrame(data = {'ndc':new_prediction_data[0][0], 'nadac_per_unit':new_prediction_data[0][1][0]}, index = [0]) #these element slices are correct
    new_prediction_data['date'] = pd.to_datetime(date, format='%Y-%m-%d')
    new_prediction_data['ndc'] = new_prediction_data['ndc'].astype(float).astype('int64')

    # Overwrite current data with new data
    historical_source.data = ColumnDataSource.from_df(new_historical)
    prediction_source.data = ColumnDataSource.from_df(new_prediction_data)

# Action when select menu changes
id_select.on_change('value', update_data)

# Set up layouts and add to document
inputs = column(id_select)

curdoc().add_root(row(inputs, plot, width = 1000))
curdoc().title = 'Drug Price Predictor'
