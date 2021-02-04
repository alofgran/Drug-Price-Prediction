import pandas as pd
import sqlite3
import os
import re

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

#Import data from SQLite
def import_db(db_parameters, *num_values, table_name):
    """
    Import data from SQLite database

    Args:
        db_parameters (dict): Database and tables names
        num_values (int): Value for LIMIT (SQL param, limiting number of returned values)

    Returns:
        pandas.DataFrame formatted data
    """
    db_path = os.path.join('dpp', 'db', db_parameters['DATABASE_NAME'])
    # db_path = 'C:/Users/Lofgran/Documents/Python Scripts/TDI/DrugPricePredictor/dpp/db/drug_data.db'
    print('Location of database: ', db_path)
    conn = sqlite3.connect(db_path)
    if num_values:
        df = pd.read_sql_query('SELECT * FROM {} LIMIT {}'.format(table_name, num_values), conn)
    else:
        df = pd.read_sql_query('SELECT * FROM {}'.format(table_name), conn)
    print('Details of imported dataframe', '\n', '--------------------------', '\n', df.info())
    conn.close()

    return df


#Creating (in)dependent variable sets (for transformation)
def split_dataset(df, dependent_var='nadac_per_unit'): #'nadac_per_unit'
    """
    Create a dataframe for the independent variable, and another for the dependent variable

    Args:
        dependent_var (str): Name of dependent variable in dataset

    Returns:
        Dataframes containing independent variable and dependent variables
    """
    X = df.drop(columns=dependent_var)
    y = df.loc[:,dependent_var]
    return X, y

#Class (and regex functions) for cleaning data
regex_fn_dict = {r'\sCAP*?\Z|\sCP*?\Z' : ' CAPSULE',
                r'\sTAB\sCHW\s*?\Z|\sTAB\sCHEW\s*?\Z': ' CHEWABLE TABLET',
                r'\sTAB\Z|\sTAB\s|\sTB' : ' TABLET',
                r'\sSYR*?\Z' : ' SYRINGE',
                r'\sCRM*?\Z' : ' CREAM',
                r'\sSL*?\Z' : ' SUB-LINGUAL',
                r'\sFOAM*?\Z' : ' FOAM',
                r'\sAUTO\-INJ*?\Z' : ' INJECTION',
                r'\sEFF*?\Z' : ' EFFERVESCENT',
                r'\sSOLN*?\Z' : ' SOLUTION',
                r'\sINH*?\Z' : ' INHALATION',
                r'\sHCL\s*?\Z' : ' HYDROCHLORIDE',
                r'\sCPLT*?\Z' : ' CAPLET',
                r'\sGASTR\s*?\Z' : ' GASTRIC',
                r'\sOSM\s*?\Z' : ' OSMOTIC',
                r'\sLIQ*?\Z' : ' LIQUID',
                r'\sP*.KT\Z' : ' PACKET', #NEW
                '\s\*\*.*\*\*\s' : '',
                ' MG' : 'MG',
                ' ML' : 'ML',
                ' MCG' : 'MCG',
                ' +': ' '
               }

class CleanNames(BaseEstimator, TransformerMixin):
    """Standardize drug names"""
    def __init__(self, regex_fn_dict, cols=[]):
        self._cols = cols
        self._regex_fn_dict=regex_fn_dict

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        #Standardize drug names with regex
        for pattern, replacement in self._regex_fn_dict.items():
            pat = re.compile(pattern)
            for col in self._cols:
                # print(col, ': ', type(col))
                if isinstance(X[col], str):
                    X[col] = X[col].str.replace(pat, replacement)
        return X

class SetDtypes(BaseEstimator, TransformerMixin):
    """Set datatypes for date columns"""
    def __init__(self, cols=[]):
        self._cols = cols

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        #Set date datatype
        for col in X[self._cols]:
            X[col] = pd.to_datetime(X[col], infer_datetime_format = True)
        return X

class RemoveData(BaseEstimator, TransformerMixin):
    """Remove unnecesseary columns and drop duplicates"""
    def __init__(self, drop_cols=[]):
        self._drop_cols = drop_cols

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        #Drop unneeded columns (many null values)
        X = X.drop(columns=self._drop_cols)
        #Drop duplicates
        X = X.drop_duplicates(keep='first')
        return X


class DrugNameNER(BaseEstimator,  TransformerMixin):
    def __init__(self, col, model_name):
        self._col = col

    def fit(self, X, y=None):
        return self
    def transform(self, X, y=None):
        nlp = spacy.load(model_name)
        #Run NLP; add results to dataframe
        X['temp'] = X.apply(lambda row: [nlp(i) for i in row])
        #Create a dictionary to save entities in
        ner_dict = {'DRUGNAME': [], 'QUANTITY': [], 'MECHANISM': []}
        for name in X['temp']:
            #If the entity was predicted NOT to exist by Ner in the drug name
            annotations_found = [i.label_ for i in name.ents]
            if 'DRUGNAME' not in annotations_found:
                print("'DRUGNAME' doesn't exist for:   {}".format(name.text))
                ner_dict['DRUGNAME'].append(None)
            elif 'QUANTITY' not in annotations_found:
                print("'QUANTITY' doesn't exist for:   {}".format(name.text))
                ner_dict['QUANTITY'].append(None)
            elif 'MECHANISM' not in annotations_found:
                print("'MECHANISM' doesn't exist for:   {}".format(name.text))
                ner_dict['MECHANISM'].append(None)

            #If the entity was predicted to exist by Ner in the drug name
            for ent in name.ents:
                if (ent.label_=='DRUGNAME'):
                    ner_dict[ent.label_].append(ent.text)

                if (ent.label_=='QUANTITY'):
                    ner_dict[ent.label_].append(ent.text)

                if (ent.label_=='MECHANISM'):
                    ner_dict[ent.label_].append(ent.text)
        X.join(pd.DataFrame(ner_dict))
        X.drop(['temp'], inplace=True)

#################################
from utils.tools import load_env_vars


df = import_db(db_parameters, *num_values, table_name)
X, y = split_dataset(df, dependent_var='nadac_per_unit')

#Build processing pipeline
pipe = Pipeline(steps=[('clean_names', CleanNames(regex_fn_dict,
                                                  cols=['ndc_description'])),
                       ('remove_data', RemoveData(drop_cols=['corresponding_generic_drug_nadac_per_unit',
                                                             'corresponding_generic_drug_effective_date',
                                                             'as_of_date'])),
                       ('set_dtypes', SetDtypes(cols=['effective_date'])),
                       ('drug_name_ner', DrugNameNER(col='ndc_description',
                                                     model_name='models/drug_names'))])
df_transform = pipe.fit_transform(df)
print(df_transform.info())
