import re
import shutil
import random
import sqlite3
import json
import requests
import sys
import os
import io
from datetime import datetime
import string
import fakeyou
import time
import wave
import audioop
import logging
import audiodb
from uuid import uuid4
from gtts import gTTS
from io import BytesIO
from pathlib import Path
from pathlib import Path
from os.path import join, dirname
from dotenv import load_dotenv
from fakeyou.objects import *
from fakeyou.exception import *
from sqlitedict import SqliteDict
from pydub import AudioSegment

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
FAKEYOU_USER = os.environ.get("FAKEYOU_USER")
FAKEYOU_PASS = os.environ.get("FAKEYOU_PASS")

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=int(os.environ.get("LOG_LEVEL")),
        datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('werkzeug')
log.setLevel(int(os.environ.get("LOG_LEVEL")))

fy=fakeyou.FakeYou()
fy.login(FAKEYOU_USER,FAKEYOU_PASS)

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
    sound.export(memoryBuff, format='mp3', bitrate="256", tags={'artist': get_voice_name("google")})
    #awesome.export("mashup.mp3", format="mp3", tags={'artist': 'Various artists', 'album': 'Best of 2011', 'comments': 'This album is awesome!'})
    memoryBuff.seek(0)
    audiodb.insert(text, memoryBuff, "google")
    return audiodb.select_by_name_voice(text, "google")

def get_tts(text: str, voice=None, timeout=600):
  try:
    if voice is None or voice == "null" or voice == "random":
      voice_to_use = get_random_voice()
    else:
      voice_to_use = voice
    if voice_to_use != "google": 
      datafy = audiodb.select_by_name_voice(text.strip(), voice_to_use)
      if datafy is not None:
        return datafy
      else:
        ijt = generate_ijt(fy, text.strip(), voice_to_use)
        if ijt is not None:
          out = get_wav_fy(fy,ijt, voice_to_use, timeout=timeout)
          if out is not None:
            audiodb.insert(text.strip(), out, voice_to_use)
            return audiodb.select_by_name_voice(text.strip(), voice_to_use)
          elif voice == "random" or voice == "google":
            return get_tts_google(text.strip())
          else:
            return None
        elif voice == "random" or voice == "google":
          return get_tts_google(text.strip())
        else:
          return None
    else:
      return get_tts_google(text.strip())
  except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)
    if voice == "random":
      return get_tts_google(text.strip())
    else:
      raise Exception(e)

def get_voice_name(voice: str):
  keys = [k for k, v in localvoices.items() if v == voice]
  return key

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


def get_wav_fy(fy,ijt:str, voice:str, timeout:int):
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
        sound.export(memoryBuff, format='mp3', bitrate="256", tags={'artist': get_voice_name(voice)})
        memoryBuff.seek(0)
        return memoryBuff
        #return fp
      elif count > timeout:
        raise RequestError("FakeYou: generation is taking longer than " + str(timeout) + " seconds, forcing timeout.")
    elif handler.status_code==429:
      raise TooManyRequests("FakeYou: too many requests.")

def login_fakeyou():
  fy.login(FAKEYOU_USER,FAKEYOU_PASS)
