from sodapy import Socrata
import os
import dotenv
import pandas as pd
import json
import re

import sqlite3
from datetime import datetime
from dateutil import parser

from utils.tools import check_build_filepath, save_to_disk, connect_to_database, save_to_SQL


def setup_socrata_client(credentials, nadac_parameters):
    """
    Setup client to access database on Socrata.

    Args:
        credentials (dict): Socrata app token from .env file
        nadac_parameters (dict): Parameters for downloading NADAC dataset from .env file
            WEBSITE: url of dataset (less 'http://www.')

    Returns:
        Socrata client
    """
    client=Socrata(nadac_parameters['WEBSITE'], credentials['APP_TOKEN'])
    client.timeout = int(nadac_parameters['TIMEOUT'])
    return client


def get_socrata_metadata(credentials, nadac_parameters):
    """
    Get metadata from socrata dataset

    Args:
        credentials (dict): Socrata app token from .env file
        nadac_parameters (dict): Parameters for downloading NADAC metadata from .env file
            DATA_LOCATION: location where metadata should be saved

    Returns:
        Nothing (saves price_metadata.json to disk)
    """
    client = setup_socrata_client(credentials, nadac_parameters)
    metadata = client.get_metadata(nadac_parameters['DATA_LOCATION'],
                                   content_type='json')

    check_build_filepath('raw_data')
    save_to_disk('raw_data/price_metadata.json', metadata)
    client.close()


def metadata_to_schema(credentials, nadac_parameters):
    """
    Convert price_metadata.json to SQLITE schema

    Args:
        credentials (dict): Socrata app token from .env file
        nadac_parameters (dict): Parameters for downloading NADAC metadata from .env file
            DATA_LOCATION: location where metadata should be saved

    Returns:
        A schema in dictionary format
    """
    #Check if metadata file exists
    if not os.path.exists('raw_data/price_metadata.json'):
        get_socrata_metadata(credentials, nadac_parameters)

    #Load metadata file
    with open('raw_data/price_metadata.json', 'r') as metadata_json:
        metadata = json.load(metadata_json)
    #Build SQL schema from metadata
    schema_dict = {i['name']:i['dataTypeName'] for i in metadata['columns']}
    for k, v in schema_dict.items():
        updates = {}
        if v == 'calendar_date':
            updates[k] = 'text'
        if re.search('.*Per_Unit', k) is not None:
            updates[k] = 'real' #SQL equivalent of float in python
        schema_dict.update(updates)
    #Fix key names
    schema_dict = {key.replace(' ', '_').lower(): val.upper() for key, val in schema_dict.items()}
    return schema_dict


def create_table_from_schema(credentials, nadac_parameters, db_parameters):
    """
    Create a SQLite table from the schema file_location_name

    Args:
        credentials (dict): Socrata app token from .env file
        nadac_parameters (dict): Parameters for downloading NADAC metadata from .env file
            DATABASE_NAME: filename of database (where table will be created)
        db_parameters (dict): parameters specific to database (table names, locations)
    Returns:
        Nothing (table is created in SQLite database)
    """
    conn = connect_to_database(os.path.join(os.getcwd(), 'db', db_parameters['DATABASE_NAME']))
    metadata_schema = metadata_to_schema(credentials, nadac_parameters)
    c = conn.cursor()
    print('Building table from schema')
    #Build table schema and execute table creation
    fieldset = ["id INT PRIMARY KEY ON CONFLICT IGNORE"] #initialized with this because doesn't exist in metadata
    for col, definition in metadata_schema.items():
        fieldset.append("'{0}' {1}".format(col, definition))
    if len(fieldset) > 0:
        query = "CREATE TABLE IF NOT EXISTS {0} ({1})".format(db_parameters['PRICES_TABLE'], ", ".join(fieldset))
    c.execute(query)
    print('Table built.')


def create_unique_id_index(dataframe, column_1, column_2):
    """
    Create unique index in dataframe to be used in sqlite database

    Args:
        dataframe (pandas.DataFrame): dataframe with which to create unique index
        column_1 (str): name of first column in dataframe to make up unique index
        column_2 (str): name of second column in dataframe to make up unique index
    Returns:
        dataframe with the new unique index
    """

    dataframe = dataframe.drop(['as_of_date'], axis=1)

    dataframe['id'] = dataframe[column_1] + dataframe[column_2]
    dataframe['id'] = dataframe.apply(lambda row: row['id'].replace('T', ''), axis=1) #remove 'T' (preceeds the time)
    dataframe['id'] = dataframe['id'].str.replace(r'[\W]', '') #Remove any non-alphaneumeric (or underscore) characters
    dataframe['id'] = dataframe['id'].str.replace(r'0{9,}', '') #Remove consecutive zeros with length > 5

    # Print out duplicate rows by index
    duplicate_rows = dataframe[dataframe.duplicated(subset=['id'])]
    print('Count of duplicate rows: ', len(duplicate_rows))
    print('Duplicated rows:', duplicate_rows, sep='\n')

    #Drop duplicates
    dataframe = dataframe[~dataframe.duplicated(subset=['id'])]

    return dataframe


def get_socrata_data(credentials, nadac_parameters, db_parameters, download_location):
    """
    Get metadata and data from Socrata database, build needed file structure,
    store the (meta)data as raw JSON, and either build an entirely new database
    (if non exists), or update the current database.

    Args:
        credentials (dict): parameters to access Socrata API
        nadac_parameters (dict): parameters to access NADAC dataset
        db_parameters (dict): parameters to access database and table for data addition
        download_location (str): location to which data should be downloaded

    Returns:
        Nothing (data is retrieved and added to database)
    """
    client = setup_socrata_client(credentials, nadac_parameters)

    #Build databasefolder if it doesn't yet exist
    # if not os.path.exists(os.path.join(os.getcwd(), 'db', db_parameters['DATABASE_NAME'])):
    #     print('No database found. Creating database.')
    check_build_filepath('db')

    #Build table if not yet created
    conn = connect_to_database(os.path.join(os.getcwd(), 'db', db_parameters['DATABASE_NAME']))
    cur = conn.cursor()
    if cur.execute("SELECT name FROM sqlite_master WHERE name='{}'".format(db_parameters['PRICES_TABLE'])).fetchone():
        print('Table already exists')
    else:
        create_table_from_schema(credentials, nadac_parameters, db_parameters)

    # Get most recent date from prices table to determine when the last date update was made
    query_date = cur.execute('SELECT MAX(effective_date) FROM {};'.format(db_parameters['PRICES_TABLE'])).fetchone()[0]
    if query_date:
        db_current_date = str(parser.parse(query_date).isoformat())
    else:
        db_current_date = query_date
    # Define current date for date comparison
    current_date = str(datetime.now().isoformat())

    # Download data
    if db_current_date == current_date:
        print('Database is already current; no update needed.')

    elif db_current_date == None: #No data in database
        # try:
        print('Downloading a fresh dataset now...')
        results = client.get(nadac_parameters['DATA_LOCATION'],
                             content_type='json',
                             limit=int(nadac_parameters['LIMIT']))
        nadac_data = pd.DataFrame(results)
        #Create unique ID index
        nadac_data = create_unique_id_index(nadac_data, 'ndc_description', 'effective_date')

        # Save file to disk
        check_build_filepath(download_location)
        with open(os.path.join(download_location, 'nadac_data.json'), 'w') as outfile:
            json.dump(nadac_data.to_json(), outfile)
        print('File saved!')
        # Push data to database
        save_to_SQL(database_name=db_parameters['DATABASE_NAME'],
                    table_name=db_parameters['PRICES_TABLE'],
                    source_df=nadac_data)
        # except:
            # print('Error downloading full database')
    else: #current date > db_current_date --> update data
        # try:
        print('Downloading updates...')
        print('Current date:     ', current_date, '\n',
              'db_current_date: ', db_current_date)
        results = client.get_all(nadac_parameters['DATA_LOCATION'],
                             content_type='json',
                             where="effective_date between '{}' and '{}'".format(db_current_date, current_date))
        nadac_data = pd.DataFrame.from_records(results)
        #Create unique ID index
        # nadac_data = create_unique_id_index(nadac_data, 'ndc', 'effective_date')
        nadac_data = create_unique_id_index(nadac_data, 'ndc_description', 'effective_date')

        # Save file to disk
        check_build_filepath(download_location)
        with open(os.path.join(download_location, 'nadac_data.json'), 'w') as outfile:
            json.dump(nadac_data.to_json(), outfile)
        print('File saved!')
        # Push data to database
        save_to_SQL(database_name=db_parameters['DATABASE_NAME'],
                    table_name=db_parameters['PRICES_TABLE'],
                    source_df=nadac_data)
    conn.close()
