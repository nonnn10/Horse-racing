import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score
import optuna
from functools import partial
from LightGBM import LightGBM
from LogisticReg import LogisticReg

# ハイパーパラメータ関数
def objective(trial, X_train, y_train, X_test, y_test):
    """最小化する目的関数"""
    # 調整するハイパーパラメータ
    params = {
        'learning_rate': trial.suggest_uniform('learning_rate', 1e-2, 1e0),
        'min_data_in_leaf': int(trial.suggest_int('min_data_in_leaf', 2, 64)),
        'feature_fraction': trial.suggest_uniform('feature_fraction', 1e-1, 1e0),
        'num_leaves':int(trial.suggest_int('num_leaves', 2, 128)),
        'drop_date': trial.suggest_uniform('drop_date', 1e-2, 1e0),
    }
    #model = xgb.XGBClassifier(**params, boosting='dart', application='binary',metric='auc')
    lgb = LightGBM(**params)
    lgb.fit(X_train,y_train) # 学習させる
    pred = lgb.predict(X_test)  # テストデータからラベルを予測する
    preds = np.round(np.abs(pred))
    return f1_score(y_true=y_test, y_pred=preds, average='micro')#accuracy_score(y_test, model.predict(X_test))#最小化なので1から正解率を引く
    

if __name__ == "__main__":
    # インスタンス生成
    lgb = LightGBM()

    # csvを読み込む
    keibaTrain = pd.read_csv("../data/201910-11.csv",sep=",")
    keibaTest = pd.read_csv("../data/arima2.csv",sep=",", encoding='shift-jis')

    category = ["Horse_Name", "Sex_Age", "Jockey", "Trainer", "Wind_Direction", "Date", 
        "Horse_Name2", "Sex_Age2", "Jockey2", "Trainer2", "Wind_Direction2", "Date2"]

    # トレインデータの前処理
    keibaTrain = lgb.preprocessing(keibaTrain)
    keibaTrain = lgb.category_encode(keibaTrain, category)

    # テストデータの前処理
    keibaTest = lgb.preprocessing(keibaTest)
    keibaTest2 = keibaTest.copy() # rankingの表示用
    keibaTest = lgb.category_encode(keibaTest, category)

    # データの準備
    X_train = keibaTrain.drop(columns="Win_or_Lose")
    y_train = keibaTrain["Win_or_Lose"]
    horse_Train = lgb.train_data(X_train, y_train)

    X_test = keibaTest.drop(columns="Win_or_Lose")
    y_test = keibaTest["Win_or_Lose"]
    horse_Test = lgb.test_data(X_test, y_test, horse_Train)

    #ハイパーパラメータ探索
    #optuna.logging.set_verbosity(optuna.logging.WARNING) # oputenaのログ出力停止
    study = optuna.create_study(direction='maximize')  # 最適化のセッションを作る,minimize,maximize
    study.optimize(lambda trial: objective(trial, horse_Train, horse_Test, X_test, y_test), n_trials=30)  # 最適化のセッションを作る
    print("ベストF１",study.best_value)
    print("ベストparam", study.best_params)

    # 学習する
    lgb = LightGBM(**study.best_params)
    lgb.fit(horse_Train, horse_Test)
    predicted = lgb.predict(X_test)
    lgb.accuracy_rate(y_test, predicted)
    # 順位を表示する
    lgb.ranking(keibaTest2, predicted)