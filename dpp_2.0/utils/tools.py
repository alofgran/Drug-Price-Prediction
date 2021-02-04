import os
import json
import sqlite3
import dotenv


def load_env_vars():
    """Finds a local '.env' file and loads the environment variables from it"""
    #Import environment variables
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    

def check_build_filepath(folder_name):
    """
    Check if folder exists in current working directory, and (if not) create it

    Args:
        folder_name (str): name of folder to be checked/created

    Returns:
        Nothing
    """
    # Make folders if nonexistant
    if not os.path.exists(folder_name):
        new_folder_path = os.path.join(os.getcwd(), folder_name)
        os.makedirs(new_folder_path)
        print('No folder "{}" found. Created folder(s) at: '.format(folder_name), new_folder_path)


def save_to_disk(file_location_name, data_to_save):
    """
    Save file to disk

    Args:
        file_location_name (str): location (+ name of file) where file should be saved
        data_to_save (object): object to be saved

    Returns:
        Nothing
    """
    with open(file_location_name, 'w') as outfile:
        json.dump(data_to_save, outfile)#added .to_json() for patent data (may cause problems for price dataset)


def connect_to_database(db_file):
    """
    Connect to SQLite database

    Args:
        db_file (str): database file name

    Returns:
        Connection object (connection to database file specified)
    """
    check_build_filepath('db')
    conn = None
    #connect to database
    try:
        conn = sqlite3.connect(db_file) #automatically creates the db file if nonexistant
        print('Connected to SQL database!')
    except sqlite3.Error as e:
        print(e)

    return conn


def get_SQL_data(db_path, num_values):
    conn = connect_to_database(os.path.join('db', db_path))
    df = pd.read_sql_query('SELECT * FROM nadac_data LIMIT {}'.format(num_values), conn)
    conn.close()
    return df


def save_to_SQL(database_name, table_name, source_df):
    """
    Add data to the database

    Args:
        database_name (str): name of database to be accessed
        table_name (str): name of table in which to insert data
        source_df (pandas.DataFrame): pandas dataframe to be added to SQLite database

    Returns:
        Nothing (data is added to database)
    """
    conn = connect_to_database(os.path.join(os.getcwd(), 'db', database_name))
    #Dropping duplicate
    print('{} new entries detected'.format(len(source_df)))
    #Load data into table
    print('Adding data to table')
    source_df.to_sql(name=table_name, con=conn, if_exists='append', index=False, index_label='id', chunksize=1000)
    print('Data added to SQL database.')
