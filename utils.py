import re
import shutil
import random
import sqlite3
import json
import requests
import sys
import os
import io
import subprocess
from datetime import datetime
import string
import fakeyou
import time
import wave
import audioop
import logging
import audiodb
from mopidyapi import MopidyAPI
from urllib.parse import urlparse
from uuid import uuid4
from gtts import gTTS
from io import BytesIO
from pathlib import Path
from os.path import join, dirname, exists
from dotenv import load_dotenv
from fakeyou.objects import *
from fakeyou.exception import *
from pydub import AudioSegment

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
FAKEYOU_USER = os.environ.get("FAKEYOU_USER")
FAKEYOU_PASS = os.environ.get("FAKEYOU_PASS")
MOPIDY_LIBRARY_DIR = os.environ.get("MOPIDY_LIBRARY_DIR")
MOPIDY_HOST = os.environ.get("MOPIDY_HOST")

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=int(os.environ.get("LOG_LEVEL")),
        datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('werkzeug')
log.setLevel(int(os.environ.get("LOG_LEVEL")))

fy=fakeyou.FakeYou()
fy.login(FAKEYOU_USER,FAKEYOU_PASS)

mopidy = MopidyAPI(host=MOPIDY_HOST, port=6680)

def get_tts_google(text: str):
  data = audiodb.select_by_name_voice(text, "google")
  if data is not None:
    return data
  else:
    tts = gTTS(text=text, lang="it", slow=False)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    sound = AudioSegment.from_mp3(fp)
    memoryBuff = BytesIO()
    voicename = get_voice_name("google")
    sound.export(memoryBuff, format='mp3', bitrate="256", tags={'artist': voicename, 'title': text}, cover=get_cover_by_name(voicename))
    memoryBuff.seek(0)
    audiodb.insert(text, memoryBuff, "google")
    return audiodb.select_by_name_voice(text, "google")

def get_cover_by_name(voicename: str):
  return os.getcwd() + "/images/" + voicename.strip().replace(" ", "_") + ".jpg"

def play_tts(text: str, voice: str):
  if mopidy.playback.get_state().lower() == "stopped" or mopidy.playback.get_state().lower() == "paused":
    if voice is None or voice == "null" or voice == "random":
      voice = get_random_voice()
    text_to_save = text
    voice_name = get_voice_name(voice).strip()
    if len(text_to_save) > 200:
      text_to_save = text_to_save[0:200]
    filename=text_to_save.strip().replace(" ", "_") + "__" + voice_name.strip().replace(" ", "_") + ".mp3"
    location=MOPIDY_LIBRARY_DIR + "/" + filename
    if exists(location):
      play_to_mopidy(text, voice)
      return 'Playing "' + text_to_save + '" using voice "' + voice_name + '"'
    else:
      tts_out, voice = get_tts(text, voice=voice)
      if tts_out is not None:
        with open(location,'wb') as out:
          out.write(tts_out.read())
          subprocess.Popen('sudo mopidyctl local scan', shell=True)
          play_to_mopidy(text, voice)
        return 'Playing "' + text_to_save + '" using voice "' + voice_name + '"'
      else:
        return None
  else:
    return 'Already playing'

def play_to_mopidy(text: str, voice: str):
  voicename = get_voice_name(voice)
  searchresult = mopidy.library.search({'artist': [voicename], 'track_name': [text]})
  if len(searchresult) > 0 and len(searchresult[0]) > 1:
    mopidy.tracklist.clear()
    mopidy.tracklist.add([searchresult[0][1][0]])
    mopidy.playback.play()
  else:
    raise Exception("Error searching for audio!")

def get_tts(text: str, voice=None, timeout=600):
  try:
    if voice is None or voice == "null" or voice == "random":
      voice_to_use = get_random_voice()
    else:
      voice_to_use = voice
    if voice_to_use != "google": 
      datafy = audiodb.select_by_name_voice(text.strip(), voice_to_use)
      if datafy is not None:
        return datafy, voice_to_use
      else:
        ijt = generate_ijt(fy, text.strip(), voice_to_use)
        if ijt is not None:
          out = get_wav_fy(fy,ijt, voice_to_use, text.strip(), timeout=timeout)
          if out is not None:
            audiodb.insert(text.strip(), out, voice_to_use)
            return audiodb.select_by_name_voice(text.strip(), voice_to_use), voice_to_use
          elif voice == "random" or voice == "google":
            return get_tts_google(text.strip()), "google"
          else:
            return None, None
        elif voice == "random" or voice == "google":
          return get_tts_google(text.strip()), "google"
        else:
          return None, None
    else:
      return get_tts_google(text.strip()), "google"
  except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)
    if voice == "random":
      return get_tts_google(text.strip()), "google"
    else:
      raise Exception(e)

def get_voice_name(voice: str):
  localvoices = get_configured_voices()
  keys = [k for k, v in localvoices.items() if v == voice]
  return str(keys[0])

def get_random_voice():
  localvoices = get_configured_voices()
  title, token = random.choice(list(localvoices.items()))
  return token

def get_configured_voices():
  localvoices = {}
  with open('voices.json') as filejson:
    loaded = json.load(filejson)
    for iterator in loaded:
      localvoices[iterator] = loaded[iterator]
  return localvoices

def list_fakeyou_voices(lang:str):
  voices=fy.list_voices(size=0)
  foundvoices = {}
		
  for langTag,voiceJson in zip(voices.langTag,voices.json):
    if lang.lower() in langTag.lower():
      foundvoices[voiceJson["title"]] = voiceJson["model_token"]
		
  return foundvoices

def generate_ijt(fy,text:str,ttsModelToken:str):
  if fy.v:
    logging.info("FakeYou - getting job token")
  payload={"uuid_idempotency_token":str(uuid4()),"tts_model_token":ttsModelToken,"inference_text":text}
  handler=fy.session.post(url=fy.baseurl+"tts/inference",data=json.dumps(payload))
  if handler.status_code==200:
    ijt=handler.json()["inference_job_token"]
    return ijt
  elif handler.status_code==400:
    raise RequestError("FakeYou: voice or text error.")
  elif handler.status_code==429:
    raise TooManyRequests("FakeYou: too many requests.")


def get_wav_fy(fy,ijt:str, voice:str, text:str, timeout:int):
  count = 0
  while True:
    handler=fy.session.get(url=fy.baseurl+f"tts/job/{ijt}")
    if handler.status_code==200:
      hjson=handler.json()
      wavo=wav(hjson)
      if fy.v:
        logging.info("FakeYou - WAV STATUS: %s", wavo.status, exc_info=1)
      if wavo.status=="started" and count <= timeout:
        continue
      elif "pending" in wavo.status and count <= timeout:
        count = count + 2
        time.sleep(2)
        continue
      elif "attempt_failed" in wavo.status and count <=2:
        raise TtsAttemptFailed("FakeYou: TTS generation failed.")
      elif "complete_success" in wavo.status and count <= timeout:
        content=fy.session.get("https://storage.googleapis.com/vocodes-public"+wavo.maybePublicWavPath).content
        fp = BytesIO(content)
        fp.seek(0)
        sound = AudioSegment.from_wav(fp)
        memoryBuff = BytesIO()
        voicename = get_voice_name(voice)
        sound.export(memoryBuff, format='mp3', bitrate="256", tags={'artist': voicename, 'title': text}, cover=get_cover_by_name(voicename))
        memoryBuff.seek(0)
        return memoryBuff
        #return fp
      elif count > timeout:
        raise RequestError("FakeYou: generation is taking longer than " + str(timeout) + " seconds, forcing timeout.")
    elif handler.status_code==429:
      raise TooManyRequests("FakeYou: too many requests.")

def login_fakeyou():
  fy.login(FAKEYOU_USER,FAKEYOU_PASS)

def reset():
  folders = ["./config" , MOPIDY_LIBRARY_DIR]
  for folder in folders:
    for filename in os.listdir(folder):
      file_path = os.path.join(folder, filename)
      if os.path.isfile(file_path) or os.path.islink(file_path):
        os.unlink(file_path)
      elif os.path.isdir(file_path):
        shutil.rmtree(file_path)
  audiodb.create_empty_tables()
  return "Reset Ok!"
