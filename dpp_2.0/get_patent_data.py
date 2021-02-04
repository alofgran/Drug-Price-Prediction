import os
from zipfile import ZipFile
from io import BytesIO
import pandas as pd
from urllib.request import urlopen
import glob
import dotenv
import json

from utils.tools import check_build_filepath, save_to_disk, connect_to_database, save_to_SQL


def get_orange_data(data_dest='raw_data', source_url='https://www.fda.gov/media/76860/download'):
    """
    Get drug patent data from The Orange Book

    Args:
        data_dest (str): Destination folder of downloaded data
        source_url (str): URL of zipped dataset

    Returns:
        Nothing (dataset is downloaded and unzipped)
    """
    current_dir = os.getcwd()
    check_build_filepath(data_dest)
    data_dir = os.path.join(current_dir, data_dest)

    # Download and unzip the patent datasets
    with urlopen(source_url) as zip_response:
        with ZipFile(BytesIO(zip_response.read())) as zfile:
            zfile.extractall(data_dir)


def merge_orange_data(data_loc='raw_data', merging_indices=['appl_no', 'product_no']):
    """
    Orange book data comes in three files.  Merge these files and save them as a single JSON

    Args:
        data_loc (str): location of the raw data (after download)
        merging_indices (list): columns on which merging will occur (should be unique in combination)

    Returns:
        Nothing (merged dataset saved as JSON to disk)
    """
    #Read in data (dictionary of dataframes with format {filename:pandas.DataFrame})
    df_dict = {}
    for root, dirs, files in os.walk(data_loc):
        for file in files:
            filename, extension = os.path.splitext(file)
            if extension == '.txt':
                df_dict[filename] = pd.read_csv(os.path.join(root, file), sep='~', engine='python')
                df_dict[filename].columns = map(str.lower, df_dict[filename].columns) #lowercase column names
    # for k, v in df_dict.items():
    #     print(k, '\n', '-----------')
    #     print(v.info())
    #     print('\n'*2)
    #Merging patent datasets
    all_patent_data = pd.merge(df_dict['products'], df_dict['patent'], on=merging_indices, how='left')
    all_patent_data = pd.merge(all_patent_data, df_dict['exclusivity'], on=merging_indices, how='left')
    #Save merged dataset to disk
    # print(all_patent_data.info())
    save_to_disk(os.path.join(data_loc, 'patent_data.json'), all_patent_data.to_json())


if __name__=='__main__':
    #Import environment variables
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)

    #Params for data storage
    db_parameters = {}
    db_parameters['DATABASE_NAME'] = os.getenv('DATABASE_NAME')
    db_parameters['PRICES_TABLE'] = os.getenv('PRICES_TABLE')
    db_parameters['PATENT_TABLE'] = os.getenv('PATENT_TABLE')

    #JSON to Pandas.DataFrame
    filepath = os.path.join('raw_data', 'patent_data.json')
    print(filepath)
    with open(filepath, "r") as read_file:
        data = json.load(read_file)
    df = pd.read_json(data)

    #Save dataframe to SQL
    save_to_SQL(db_parameters['DATABASE_NAME'], db_parameters['PATENT_TABLE'], df)
