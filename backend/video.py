import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from dotenv import load_dotenv
from facenet_pytorch import MTCNN
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from moviepy.editor import ImageSequenceClip, VideoFileClip
from PIL import Image, ImageDraw
from tqdm.notebook import tqdm
from transformers import (
    AutoConfig,
    AutoFeatureExtractor,
    AutoModelForImageClassification,
)

load_dotenv()

os.environ['XDG_CACHE_HOME'] = '/home/uncanny/.cache'
os.environ['HUGGINGFACE_HUB_CACHE'] = '/home/uncanny/.cache'

extractor = AutoFeatureExtractor.from_pretrained("trpakov/vit-face-expression")
model = AutoModelForImageClassification.from_pretrained("trpakov/vit-face-expression")

# Добавляем логирование 
logging.basicConfig(
    filename="logfile.log",
    level=logging.INFO,
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
logger.info("Running on device: {}".format(device))

# Инициализация MTCNN-модели
mtcnn = MTCNN(
    image_size=160,
    margin=0,
    min_face_size=200,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=True,
    keep_all=False,
    device=device,
)

# Цвета для разных эмоций
colors = {
    "angry": "red",
    "disgust": "green",
    "fear": "gray",
    "happy": "yellow",
    "neutral": "purple",
    "sad": "blue",
    "surprise": "orange",
}


def load_video(scene: str):
    clip = VideoFileClip(scene)

    vid_fps = clip.fps
    video = clip.without_audio()
    video_data = np.array(list(video.iter_frames()))

    return vid_fps, video, video_data


def detect_emotions(image):
    """Обнаруживает эмоцию по данному изображению

    :param image: Фотография (кадр видео)
    :return: Лицо и вероятность принадлежности к классу (tuple(face, class_probabilities)), если найдено. Иначе - tuple(None, None)
    """
    temporary = image.copy()

    # Поиск лиц на изображении с помощью MTCNN модели
    sample = mtcnn.detect(temporary)
    if sample[0] is not None:
        box = sample[0][0]

        # Обрезаем лицо
        face = temporary.crop(box)

        inputs = extractor(images=face, return_tensors="pt")

        outputs = model(**inputs)

        # Применяем softmax к logits чтобы получить вероятности
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # Получаем id2label атрибут из конфигураций
        config = AutoConfig.from_pretrained("trpakov/vit-face-expression")
        id2label = config.id2label

        probabilities = probabilities.detach().numpy().tolist()[0]

        class_probabilities = {
            id2label[i]: prob for i, prob in enumerate(probabilities)
        }

        return face, class_probabilities
    return None, None


def create_combined_image(face, class_probabilities):
    """
    Объединяет найденное лицо со столбчатой диаграммой (для красоты)

    :param face: Лицо
    :param class_probabilities: Вероятность принадлежности к классу
    :return: Объединенное изображение
    """

    palette = [colors[label] for label in class_probabilities.keys()]

    fig, axs = plt.subplots(1, 2, figsize=(15, 6))
    axs[0].imshow(np.array(face))
    axs[0].axis("off")

    sns.barplot(
        ax=axs[1],
        y=list(class_probabilities.keys()),
        x=[prob * 100 for prob in class_probabilities.values()],
        palette=palette,
        orient="h",
    )
    axs[1].set_xlabel("Probability (%)")
    axs[1].set_title("Emotion Probabilities")
    axs[1].set_xlim([0, 100])

    canvas = FigureCanvas(fig)
    canvas.draw()
    img = np.frombuffer(canvas.tostring_rgb(), dtype="uint8")
    img = img.reshape(canvas.get_width_height()[::-1] + (3,))

    plt.close(fig)
    return img


def video_pipeline(file_path: str, doGraph: bool) -> tuple:
    """
    Пайплайн для обработки видео

    :param file_path: Путь к видео-файлу
    :param doGraph: Делать ли график
    :return: tuple: Путь к gif и None | Путь к gif и путь к графику
    """
    vid_fps, video, video_data = load_video(file_path)
    filename = os.path.basename(file_path)

    skips = 2
    reduced_video = []

    for i in tqdm(range(0, len(video_data), skips)):  
        """Укорачиваем видео в 2 раза в угоду оптимизации. 
        Можно и больше, главное - расчитать сколько милисекунд 
        в среднем длится человеческая эмоция, 
        затем можно привязать это к video_fps"""
        reduced_video.append(video_data[i])

    # Список наших эмоций
    emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

    # Список для хранения комбинированных изображений из create_combined_image()
    combined_images = []

    # Список для хранения вероятностей всех классов
    all_class_probabilities = []

    # Проходимся по всем кадрам в видео
    for i, frame in tqdm(enumerate(reduced_video),
                        total=len(reduced_video),
                        desc="Processing frames"):
        
        # Рассматриваем кадры в типе uint8
        frame = frame.astype(np.uint8)

        # Получаем лицо и эмоции
        face, class_probabilities = detect_emotions(Image.fromarray(frame))
        
        if face is not None:
            # Создаем комбинированное изображение, если лицо найдено
            combined_image = create_combined_image(face, class_probabilities)
            combined_images.append(combined_image)
        else:
            class_probabilities = {emotion: None for emotion in emotions}
            
        all_class_probabilities.append(class_probabilities)

    # Создаем видео-клип из всех наших кадров
    clip_with_plot = ImageSequenceClip(combined_images,
                                    fps=vid_fps/skips)  # Здесь можно задать нужный fps выходного видео

    # Сохраняем файл
    gif_path = f"./report/{filename[:filename.find('.')]}.mp4"
    clip_with_plot.write_videofile(f"./report/{filename[:filename.find('.')]}.mp4", fps=vid_fps/skips)

    # Преобразуем список вероятностей в DataFrame
    df = pd.DataFrame(all_class_probabilities)

    df = df * 100

    # Интерполируем проопущенные значения, чтобы график не выглядил "рваным"
    df.interpolate(method='linear', inplace=True)

    fig, axs = plt.subplots(len(df.columns), 1, figsize=(15, 8), sharex=True)

    for i, emotion in enumerate(df.columns):
        axs[i].plot(df[emotion], color=colors[emotion])
        axs[i].set_ylabel('Вероятность (%)')
        axs[i].set_title(emotion.capitalize())



    if doGraph:
        plt.xlabel('Кадр')
        fig.suptitle('Вероятность эмоции на тайм-лайне')
        plt.tight_layout()
        fig_path = f"./report/{filename[:filename.find('.')]}_graph.png"
        plt.savefig(f"./report/{filename[:filename.find('.')]}_graph.png")

        return gif_path, fig_path

    return gif_path, None
