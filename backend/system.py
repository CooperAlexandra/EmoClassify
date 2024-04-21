import io
import json
import logging
import os
import re
import shutil
import time
from unicodedata import normalize

import chardet
import magic
from moviepy.editor import VideoFileClip
from pydub import AudioSegment

# Добавляем логирование
logging.basicConfig(
    filename="logfile.log",
    level=logging.INFO,
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {"wav"}
VIDEO_EXTENSIONS = {"mp4"}
ALLOWED_EXTENSIONS = {"wav", "mp4"}
ALLOWED_MIMES = {
    "WAVE audio",
    "ISO Media",
    "MP4",
    "Ogg data",
    "WebM",
    "MPEG ADTS",
    "ID3",
}


def delete_files_with_substring(folder: str, substring: str = "") -> None:
    """
    Удаляет файлы последней сессии из директории и проверяет
    ее на существование
    :param folder: Название директории
    :param substring: Имя подстроки для поиска файла по имени
    """
    # Проверяем существование директории, и если ее нет, создаем
    if not os.path.exists(folder):
        os.makedirs(folder)
        logger.info(f"Folder {folder} created")
        return

    if substring == "":
        shutil.rmtree(folder)
        os.makedirs(folder)
        logger.info(f"Folder {folder} updated")

    else:
        files = os.listdir(folder)
        for file in files:
            if substring in file:
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.info(f"File {file_path} deleted")


def get_encoding(txt_file_path: str) -> str:
    """
    Получает тип кодирования файла
    :param txt_file_path: Путь к текстовому файлу
    :return: Тип кодирование файла
    """
    with io.open(txt_file_path, "rb") as txt_file:
        result = chardet.detect(txt_file.read())

    logger.info(f"Получено кодирование файла: {result['encoding']}")
    return result["encoding"]


def converter(filename: str, upload_dir: str = "uploaded_files") -> str:
    """
    Конвертирует исходный аудио- или видео-файлв в формат .wav
    :param filename: имя файла
    :param upload_dir: директория, в которой находится загруженный файл
    :return: имя конвертированного файла
    """

    output_file = os.path.join(upload_dir, filename[: filename.find(".")] + ".wav")

    audio = AudioSegment.from_file(filename)
    audio.export(output_file, format="wav")

    filename = filename[: filename.find(".")] + ".wav"

    return filename


def allowed_file(filename: str) -> bool:
    """
    Проверяет разрешенность файла на основе его расширения и MIME-типа
    :param filename: Имя файла (с его путем)
    :return: Булевое значение (True/False)
    """

    # Проверяем содержит ли имя файла точку (.)
    if "." not in filename[1:]:
        return False

    # Получаем расширение файла
    file_extension = filename.rsplit(".", 1)[1].lower()

    # Проверяем содержится ли расширение файла в списке разрешенных
    if file_extension not in ALLOWED_EXTENSIONS:
        return False

    mime = magic.Magic()

    # Получаем MIME тип файла
    file_mt = mime.from_file(filename)

    # Проверяем, содержится ли MIME-тип файла в списке разрешенных
    if not any(allowed_type in file_mt for allowed_type in ALLOWED_MIMES):
        return False

    return True


_windows_device_files = (
    "CON",
    "AUX",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "LPT1",
    "LPT2",
    "LPT3",
    "PRN",
    "NUL",
)

_filename_strip_re = re.compile(r"[^A-Za-zа-яА-ЯёЁ0-9_.-]")


def secure_filename(filename: str) -> str:
    """
    Функция-замещение werkzeug.utils.secure_filename
    с поддержкой русского языка
    :param filename: имя файла
    :return: строка, секьюрное имя файла
    """
    if isinstance(filename, str):
        filename = normalize("NFKD", filename)

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")

    filename = str(_filename_strip_re.sub("", "_".join(filename.split()))).strip("._")

    if (
        os.name == "nt"
        and filename
        and filename.split(".")[0].upper() in _windows_device_files
    ):
        filename = f"_{filename}"

    return filename


def convert_mp4_to_wav(file: str | os.PathLike) -> str | os.PathLike:
    # Загрузить видео из файла MP4
    video_clip = VideoFileClip(file)

    # Получить аудиодорожку из видео
    audio_clip = video_clip.audio

    wav_file_path = file[: file.find(".")] + ".wav"

    # Сохранить аудиодорожку в формате WAV
    audio_clip.write_audiofile(wav_file_path)

    return wav_file_path
