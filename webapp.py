import os
from pathlib import Path

import streamlit as st

from backend import system
from backend.audio import predict_voice
from backend.report import create_report, generate_report_text
from backend.system import ALLOWED_EXTENSIONS
from backend.video import video_pipeline

# Используем прямую связь с api как с библиотекой потому что API Gateway и MVP Streamlit Webapp будут располагаться на одном сервере
from callback import api

st.title("Интеллектульный модуль распознавания эмоций")

# Загрузчик файлов, пока-что поддерживает только загрузку одного файла
file = st.file_uploader(
    "Загрузите аудио или видео-файл",
    type=list(ALLOWED_EXTENSIONS),
    accept_multiple_files=False,
)

session = {
    "filename": None,  # Имя файла
    "file_type": None,  # Тип файла из функции video_or_audio()
    "report": None,  # Cоставить отчет о проделанной работе
    "make_graph": None,  # Нарисовать график для всей дорожки, показывающий эмоции
    # "echo_mean": None,  # Добавить в ответ среднюю эмоцию для всего разговора
    # "transcribe": None,  # Добавить в ответ расшифровку разговора
    # "transcribe_focus": None,  # Показать эмоции в словах, к которым они принадлежат (работает только при "transcribe": True)
    "double_check": None,  # Добавить проверку эмоции в видео с помощью анализа аудио-дорожки (работате толкьо при "file_type": "video")
}

if file:
    session["filename"] = file.name
    session["file_type"] = api.video_or_audio(session["filename"])
    if session["file_type"] == "video":
        session["double_check"] = st.checkbox("Добавить анализ аудио дорожки для файла")
        session["make_graph"] = st.toggle(
            "Нарисовать график распределения эмоций по тайм-лайну"
        )

session["report"] = st.toggle("Созать отчет")


start = st.button("Начать")
if start:
    FOLDERS = ["report", "uploaded_files"]
    for folder in FOLDERS:
        if not os.path.exists(folder):
            os.mkdir(folder)
    save_path = Path(FOLDERS[1], session["filename"])
    with open(save_path, mode="wb") as w:
        w.write(file.getvalue())

    if session["file_type"] == "video":
        gif_path, fig_path = video_pipeline(
            os.path.join(FOLDERS[1], session["filename"]), session["make_graph"]
        )
        st.write("Видео зафиксированных лиц и эмоций:")
        video_file = open(gif_path, "rb")
        video_bytes = video_file.read()
        st.video(video_bytes)
        if fig_path is not None:
            st.write("График распределения эмоций по таймлайну")
            st.image(fig_path)

        if session["double_check"]:
            # Вызываем метод анализа для видео с предварительной конвертацией видео в .wav формат
            filename = system.convert_mp4_to_wav(
                os.path.join(FOLDERS[1], session["filename"])
            )
            audio_answer = predict_voice(filename)
            st.write(
                f"Оценка аудио-дорожки файла показала результат средней эмоции: {audio_answer}"
            )

    else:
        audio_answer = predict_voice(os.path.join(FOLDERS[1], session["filename"]))
        st.write(
            f"Оценка аудио-дорожки файла показала результат средней эмоции: {audio_answer}"
        )

    if session["report"]:
        report_text = generate_report_text(session["filename"], audio_answer)
        st.write(report_text)
