import pyaudio
import boto3
import requests
import time
import keyboard
import uuid
import os
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv('API_KEY')
POST = 'https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize'
ENDPOINT = "https://storage.yandexcloud.net"

audio_format = pyaudio.paInt16
channels = 1
sample_rate = 44100
chunk_size = 1024
file_name = str(uuid.uuid4()) + '.mp3'

print('Нажмите пробел для начала записи, нажмите снова для окончания.')
keyboard.wait(" ")
audio = pyaudio.PyAudio()
stream = audio.open(format=audio_format,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=chunk_size)

print('Запись аудио...')

frames = []

while True:
    data = stream.read(chunk_size)
    frames.append(data)
    if keyboard.is_pressed(" "): 
        print('Запись завершена. Начинаем распознавание...')
        break

stream.stop_stream()
stream.close()
audio.terminate()

audio_data = b''.join(frames)
audio_segment = AudioSegment(
    audio_data,
    sample_width=audio.get_sample_size(audio_format),
    frame_rate=sample_rate,
    channels=channels
)

audio_segment.export(file_name, format="mp3")

session = boto3.session.Session(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name="ru-central1",
)

s3 = session.client("s3", endpoint_url=ENDPOINT)

s3.upload_file(file_name, os.getenv('BUCKET_NAME'), file_name)

presigned_url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": os.getenv('BUCKET_NAME'), "Key": file_name},
    ExpiresIn=100,
)

body = {
    "config": {
        "specification": {
            "languageCode": "ru-RU",
            "audioEncoding": "MP3"
        }
    },
    "audio": {
        "uri": presigned_url
    }
}

header = {'Authorization': 'Api-Key {}'.format(KEY)}

req = requests.post(POST, headers=header, json=body)
data = req.json()

id = data['id']

while True:

    time.sleep(1)

    GET = "https://operation.api.cloud.yandex.net/operations/{id}"
    req = requests.get(GET.format(id=id), headers=header)
    req = req.json()

    if req['done']:
        break
    print('Распознаем...')

print('Распознанный текст:')
for chunk in req['response']['chunks']:
    print(chunk['alternatives'][0]['text'])


