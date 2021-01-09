import pandas as pd
import numpy as np
import os
import glob
import random
import math
import warnings
warnings.filterwarnings("ignore")

train = pd.read_csv('./data/train/train.csv')
submission = pd.read_csv('./data/sample_submission.csv')

def preprocess_data(data, is_train=True):
    
    temp = data.copy()
    temp = temp[['Hour', 'Minute','TARGET', 'DHI','DNI','WS', 'RH', 'T']]
    temp = temp.assign(GHI=lambda x: x['DHI'] + x['DNI'] * np.cos(((180 * (x['Hour']+1+x['Minute']/60) / 24) - 90)/180*np.pi))
    temp = temp[['Hour', 'TARGET','GHI','DHI','DNI','RH','T','WS']]
    
    if is_train==True:
        temp['Target1'] = temp['TARGET'].shift(-48).fillna(method='ffill')
        temp['Target2'] = temp['TARGET'].shift(-48*2).fillna(method='ffill')
        return temp.iloc[:-96] 

    elif is_train==False:  
        return temp.iloc[-48:, :]

df_train = preprocess_data(train)
test = []

for i in range(81):
    file_path = './data/test/' + str(i) + '.csv'
    temp = pd.read_csv(file_path)
    temp = preprocess_data(temp, is_train=False).iloc[-48:]
    test.append(temp)

X_test = pd.concat(test)

from sklearn.model_selection import train_test_split
X_train_1, X_valid_1, Y_train_1, Y_valid_1 = train_test_split(df_train.iloc[:, :-2], df_train.iloc[:, -2], test_size=0.3, random_state=0)
X_train_2, X_valid_2, Y_train_2, Y_valid_2 = train_test_split(df_train.iloc[:, :-2], df_train.iloc[:, -1], test_size=0.3, random_state=0)

quantiles = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

params = {
    'objective': 'quantile',
    'metric': 'quantile',
    #'max_depth': -1,
    #'num_leaves': 144,
    #'num_iterations' : 1000,
    'learning_rate': 0.01,
    'n_estimators': 10000,
    #'min_data_in_leaf':600,
    'boosting_type': 'dart'
}
from tensorflow.keras.backend import mean, maximum

def quantile_loss(q, y, pred):
      err = (y-pred)
      return mean(maximum(q*err, (q-1)*err), axis=-1)
# 2. 모델 구성
from keras.models import Sequential
from keras.layers import Dense
def LGBM(q, X_train, Y_train, X_valid, Y_valid, X_test):
  model = Sequential()
  model.add(Dense(10, activation='relu'))
  model.add(Dense(10))
  model.add(Dense(8))
  model.add(Dense(1))
  # 3. 훈련
  model.compile(loss=lambda y,pred: quantile_loss(q,y,pred), optimizer='adam')
  model.fit(X_train, Y_train, epochs=100)
  pred = pd.Series(model.predict(X_test).round(2))
  return pred, model

def train_data(X_train, Y_train, X_valid, Y_valid, X_test):
    
    models=[]
    actual_pred = pd.DataFrame()

    for q in quantiles:
        print(q)
        pred , model = LGBM(q, X_train, Y_train, X_valid, Y_valid, X_test)
        models.append(model)
        actual_pred = pd.concat([actual_pred,pred],axis=1)

    LGBM_actual_pred.columns=quantiles
    
    return models, actual_pred

models_1, results_1 = train_data(X_train_1, Y_train_1, X_valid_1, Y_valid_1, X_test)
models_2, results_2 = train_data(X_train_2, Y_train_2, X_valid_2, Y_valid_2, X_test)

submission.loc[submission.id.str.contains("Day7"), "q_0.1":] = results_1.sort_index().values
submission.loc[submission.id.str.contains("Day8"), "q_0.1":] = results_2.sort_index().values

submission.to_csv('./data/submission.csv', index=False)