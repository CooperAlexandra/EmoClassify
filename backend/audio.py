import math

import librosa
import numpy as np
import tensorflow as tf

model = tf.keras.models.load_model("./voice_model/model3.h5")

emotion_enc = {
    "Страх": 0,
    "Отвращение": 1,
    "Нейтральность": 2,
    "Счастье": 3,
    "Грусть": 4,
    "Удивление": 5,
}


def get_key_by_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None


def predict_voice(file_path: str) -> str:
    """
    Загружает аудио-файл и передает его в модель

    :param file_path: Путь к аудио-файлу
    :return: Ответ от модели
    """
    x, sr = librosa.load(file_path, sr=44000)
    length_chosen = 115181

    if x.shape[0] > length_chosen:
        new = x[:length_chosen]
    elif x.shape[0] < length_chosen:
        new = np.pad(x, math.ceil((length_chosen - x.shape[0]) / 2), mode="median")
    else:
        new = x

    mfcc = librosa.feature.mfcc(y=new, sr=44000, n_mfcc=40)
    mfcc = mfcc.T

    mfcc = mfcc.reshape(1, 225, 40)
    predict = model.predict(mfcc)

    answer = predict.argmax()

    return get_key_by_value(emotion_enc, answer)
