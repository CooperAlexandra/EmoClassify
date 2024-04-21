import logging
import os

from dotenv import load_dotenv
from flask import Flask, Request, Response, jsonify, request, send_file
from flask.logging import default_handler
from flask_cors import CORS

from backend import system
from backend.audio import predict_voice
from backend.report import create_report, generate_report_text
from backend.video import video_pipeline

load_dotenv()

HOST_ADRESS = os.getenv("HOST_ADRESS")
BACKEND_PORT = os.getenv("BACKEND_PORT")
FOLDERS = ["uploaded_files", "report"]
REQUIRED_SETTINGS = []

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1000 * 1000 * 1000  # 2Gb
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["UPLOAD_FOLDER"] = "uploaded_files"
CORS(app)

for folder in FOLDERS:
    if not os.path.exists(folder):
        os.mkdir(folder)


# Flask-логгирование
logging.basicConfig(
    filename="logfile.log",
    level=logging.INFO,
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
default_handler = logging.StreamHandler()
logger.addHandler(default_handler)


def check_type(path: str) -> int:
    """Функция для обработки ответа от system модуля

    :param path: Путь к файлу
    :return: Код обработки
    """
    isType, file_mt = system.allowed_file(path)
    if not isType:
        return 415
    return 200


def video_or_audio(filename: str) -> str:
    """Функция определяет к какому типу относится файл видео или аудио

    :param filename: Имя файла с его расширением
    :return: Тип файла
    """
    file_extension = filename.rsplit(".", 1)[1].lower()
    if file_extension in system.VIDEO_EXTENSIONS:
        return "video"
    return "audio"


def load_request_params(request: Request) -> dict:
    """Функция загрузки параметров из запроса

    :param request: Запрос
    :raises e: Точка останова при ошибке
    :return: Словарь, содержащий настройки сессии
    """
    session = {
        "filename": None,  # Имя файла
        "file_type": None,  # Тип файла из функции video_or_audio()
        "report": False,  # Cоставить отчет о проделанной работе
        "make_graph": False,  # Нарисовать график для всей дорожки, показывающий эмоции
        # "echo_mean": False,  # Добавить в ответ среднюю эмоцию для всего разговора
        # "transcribe": False,  # Добавить в ответ расшифровку разговора
        # "transcribe_focus": False,  # Показать эмоции в словах, к которым они принадлежат (работает только при "transcribe": True)
        "double_check": False,  # Добавить проверку эмоции в видео с помощью анализа аудио-дорожки (работате толкьо при "file_type": "video")
    }
    try:
        session["report"] = request.form.get("report", False)
        session["make_graph"] = request.form.get("make_graph", False)
        session["transcribe"] = request.form.get("transcribe", False)
        session["transcribe_focus"] = request.form.get("transcribe_focus", False)

        logger.info(f"[flask] All request params sucessfully loaded")

        # Проверка наличия всех нужных параметов  в настройках
        for key in REQUIRED_SETTINGS:
            if key not in session or session[key] == "error":
                logger.error(f"[flask] Missing required setting: {key}")
                raise ValueError

        file = request.files["file"].filename
        filename = system.secure_filename(file.filename)
        if filename == "":
            logger.error(f"[flask] File name must contain name and extension")
            raise ValueError

        session["file_type"] = video_or_audio(filename)

        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)
        logger.info(f"[flask] File saved")

        # Проверка файла на тип данных
        status_code = check_type(path)
        if status_code != 200:
            raise "File data type is broken"

        session["filename"] = filename
        return session

    except Exception as e:
        logger.error(f"[flask] Exception while loading parameters: {e}")
        raise e


@app.route("/upload", methods=["POST"])
def handle_file_upload():
    """
    Пайплайн для API


    """
    request._load_form_data  # Загружаем данные переданные в формате form_data

    session: dict = load_request_params(request)

    response = {}
    figure = None
    gif = None

    if session["file_type"] == "video":
        gif_path, fig_path = video_pipeline(
            os.path.join(app.config["UPLOAD_FOLDER"], session["filename"]),
            session["make_graph"],
        )
        gif = send_file(gif_path, as_attachment=True)

        if session["double_check"]:
            # Вызываем метод анализа для видео с предварительной конвертацией видео в .wav формат
            filename = system.convert_mp4_to_wav(
                os.path.join(app.config["UPLOAD_FOLDER"], session["filename"])
            )
            answer = predict_voice(filename)
            response["audio_answer"] = answer
    else:
        answer = predict_voice(
            os.path.join(app.config["UPLOAD_FOLDER"], session["filename"])
        )
        response["audio_answer"] = answer

    if session["report"]:
        report_text = generate_report_text(session["filename"], answer)
        if fig_path:
            report_name = create_report(report_text, session["filename"], fig_path)
            report_path = os.path.join("report", report_name)
            report = send_file(report_path, as_attachment=True)

            figure = send_file(fig_path, as_attachment=True)
        else:
            report_name = create_report(report_text, session["filename"])
            report_path = os.path.join("report", report_name)
            report = send_file(report_path, as_attachment=True)

    return response, figure, gif, report


if __name__ == "__main__":
    app.run(host=HOST_ADRESS, port=BACKEND_PORT, debug=True)
