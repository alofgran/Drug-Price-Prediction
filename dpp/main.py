import get_price_data
import os
from datetime import datetime
from utils.tools import load_env_vars

from sklearn.pipeline import Pipeline
from data_cleaner import CleanNames, RemoveData, SetDtypes, DrugNameNER

if __name__ == '__main__':

    load_env_vars()

    #Credentials to access Socrata dataset
    credentials = {}
    credentials['APP_TOKEN'] = os.getenv('APP_TOKEN')

    #Parameters to access NADAC dataset
    nadac_parameters = {}
    nadac_parameters['LIMIT'] = os.getenv('LIMIT')
    nadac_parameters['WEBSITE'] = os.getenv('WEBSITE')
    nadac_parameters['DATA_LOCATION'] = os.getenv('DATA_LOCATION')
    nadac_parameters['TIMEOUT'] = os.getenv('TIMEOUT')
    nadac_parameters['CURRENT_DATE'] = datetime.now().isoformat()
    nadac_parameters['LAST_DOWNLOADED'] = os.getenv('LAST_DOWNLOADED')

    #Params for data storage
    db_parameters = {}
    db_parameters['DATABASE_NAME'] = os.getenv('DATABASE_NAME')
    db_parameters['PRICES_TABLE'] = os.getenv('PRICES_TABLE')
    db_parameters['PATENT_TABLE'] = os.getenv('PATENT_TABLE')

    #Download new data or update database
    df = get_price_data.get_socrata_data(credentials, nadac_parameters, db_parameters, 'raw_data')

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
