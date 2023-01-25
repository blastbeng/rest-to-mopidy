import os
import sqlite3
import logging

from io import BytesIO
from dotenv import load_dotenv
from os.path import dirname
from os.path import join
from pathlib import Path
from datetime import datetime

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=int(os.environ.get("LOG_LEVEL")),
        datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('werkzeug')
log.setLevel(int(os.environ.get("LOG_LEVEL")))

def check_db_exists(): 
  fle = Path("./config/audiodb.sqlite3")
  fle.touch(exist_ok=True)
  f = open(fle)
  f.close()

def create_empty_tables():
  check_db_exists()
  try:
    sqliteConnection = sqlite3.connect("./config/audiodb.sqlite3")
    cursor = sqliteConnection.cursor()

    sqlite_create_audio_query = """ CREATE TABLE IF NOT EXISTS Audio(
            id INTEGER PRIMARY KEY,
            name VARCHAR(500) NOT NULL,
            data BLOB NOT NULL,
            voice VARCHAR(50) NOT NULL,
            UNIQUE(name,voice)
        ); """

    cursor.execute(sqlite_create_audio_query)

  except sqlite3.Error as error:
    logging.error("Failed to create tables: %s %s %s", exc_info=1)
  finally:
    if sqliteConnection:
        sqliteConnection.close()

def insert(name: str, data: BytesIO, voice: str):
  try:
    sqliteConnection = sqlite3.connect("./config/audiodb.sqlite3")
    cursor = sqliteConnection.cursor()

    sqlite_insert_audio_query = """INSERT INTO Audio
                          (name, data, voice) 
                           VALUES 
                          (?, ?, ?)"""

    data_audio_tuple = (name, 
                        data.read(),
                        voice)

    cursor.execute(sqlite_insert_audio_query, data_audio_tuple)


    sqliteConnection.commit()
    cursor.close()

  except sqlite3.Error as error:
    logging.error("Failed to insert data into sqlite", exc_info=1)
  finally:
    if sqliteConnection:
        sqliteConnection.close()

def select_by_name_voice(name: str, voice: str):
  audio = None
  try:
    sqliteConnection = sqlite3.connect("./config/audiodb.sqlite3")
    cursor = sqliteConnection.cursor()

    sqlite_select_query = """SELECT data from Audio WHERE name = ? AND voice = ? """
    cursor.execute(sqlite_select_query, (name, voice,))
    records = cursor.fetchall()

    for row in records:
      data   =  row[0]
      cursor.close()
      audio = BytesIO(data)
      audio.seek(0)

  except sqlite3.Error as error:
    logging.error("Failed to read data from sqlite table", exc_info=1)
  finally:
    if sqliteConnection:
      sqliteConnection.close()
  return audio

def select_audio_by_id(id: int):
  audio = None
  try:
    sqliteConnection = sqlite3.connect("./config/audiodb.sqlite3")
    cursor = sqliteConnection.cursor()

    sqlite_select_query = """SELECT data from Audio WHERE id = ? """
    cursor.execute(sqlite_select_query, (id,))
    records = cursor.fetchall()

    for row in records:
      data   =  row[0]
      cursor.close()
      audio = BytesIO(data)
      audio.seek(0)

  except sqlite3.Error as error:
    logging.error("Failed to read data from sqlite table", exc_info=1)
  finally:
    if sqliteConnection:
      sqliteConnection.close()
  if audio is None:
    raise Exception("Audio not found")
  else:
    return audio



def delete_by_name(name: str):
  try:
    dbfile="./config/audiodb.sqlite3"
    sqliteConnection = sqlite3.connect(dbfile)
    cursor = sqliteConnection.cursor()

    sqlite_delete_query = "DELETE FROM Audio WHERE chatid = '" + chatid + "' and (name like '" + name + "%' OR name like '%" + name + "' OR name LIKE '%" + name + "%' OR name = '" + name + "') COLLATE NOCASE"

    data_tuple = ()

    logging.info("delete_from_audiodb_by_text - Executing:  %s", sqlite_delete_query, exc_info=1)

    cursor.execute(sqlite_delete_query, data_tuple)
    sqliteConnection.commit()
    cursor.close()

  except sqlite3.Error as error:
    logging.error("Failed to delete data from sqlite", exc_info=1)
  finally:
    if sqliteConnection:
        sqliteConnection.close()