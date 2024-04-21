# EmoClassify

## URL: https://emoclassify-hyghbgxbyhctyncoiztwoh.streamlit.app/

### Распознавание эмоций в аудио файле 
(/voice_model/combine_datasets.ipynb & /voice_model/model.ipynb)

Для обучения сверточной нейронной сети использовали датасеты: CREMA-D, RAVDESS, SAVEE и TESS. Получили из них размеченные данные, привели к общему, понятному, виду. Соеденили в единый датафрейм суммарно более 2200 строк. \
Сверточную нейронную сеть обучали 3 раза, каждый раз добавляя новые слои Dropout, MaxPoling1D и Dense для избежания переобучения и повышения точности модели. В результате получили модель с 273,289 параметрами точностью 0.87 и F-1 score 0.89 

| Layer (type)                     | Output Shape           | Param #    |
|----------------------------------|------------------------|------------|
| conv1d_19 (Conv1D)               | (None, 225, 256)       | 51,456     |
| activation_24 (Activation)       | (None, 225, 256)       | 0          |
| max_pooling1d_18 (MaxPooling1D)  | (None, 28, 256)        | 0          |
| dropout_16 (Dropout)             | (None, 28, 256)        | 0          |
| conv1d_20 (Conv1D)               | (None, 28, 128)        | 163,968    |
| activation_25 (Activation)       | (None, 28, 128)        | 0          |
| max_pooling1d_19 (MaxPooling1D)  | (None, 7, 128)         | 0          |
| dropout_17 (Dropout)             | (None, 7, 128)         | 0          |
| flatten_9 (Flatten)              | (None, 896)            | 0          |
| dense_17 (Dense)                 | (None, 64)             | 57,408     |
| dense_18 (Dense)                 | (None, 7)              | 455        |
| activation_26 (Activation)       | (None, 7)              | 0          |


### Распознавание эмоций в видео файле 
(video.ipynb (тесты) & /backend/video.py)

Взяли предобученную модель для распознавания эмоций по фото (trapakov/vit-face-expression), поставили ей в пару модель MTCNN из библиотеки facenet_pytorch с параметрами: 
```python
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
```
Каждое видео разделили на кадры с пропуском каждого второго (расчет идет на то, что за 1 кадр человек не успеет показать и поменять эмоцию. Можно настраивать параметр в зависимости от fps видео), определили наличие лица и, если оно есть, определили эмоцию. \
Все такие картинки мы сопроводили столбчатыми диаграммами уверенности модели и объедениили в видео ряд для отслеживания динамики. Дополнительно можно создавать график, показывающий изменение эмоций на таймлайне.

### API 
(/callback/api.py)

Rest API реализовали на Flask. Api принимает на вход файл и параметры к нему. Может опционально возвращать пользователю проверку аудио сигнала на эмоцию (для видео), график эмоций на таймлайне, видео изменения эмоций, оценки моделей и отчет. Параметры API:
```python
{
        "filename": None,  # Имя файла
        "file_type": None,  # Тип файла из функции video_or_audio()
        "report": False,  # Cоставить отчет о проделанной работе
        "make_graph": False,  # Нарисовать график для всей дорожки, показывающий эмоции
        # "echo_mean": False,  # Добавить в ответ среднюю эмоцию для всего разговора
        # "transcribe": False,  # Добавить в ответ расшифровку разговора
        # "transcribe_focus": False,  # Показать эмоции в словах, к которым они принадлежат (работает только при "transcribe": True)
        "double_check": False,  # Добавить проверку эмоции в видео с помощью анализа аудио-дорожки (работате толкьо при "file_type": "video")
    }
```

### Webapp 
(webapp.py)

Веб-приложение реализовали на Streamlit. Приложение полностью дублирует функционал API и обращается к нему. Интерфейс сделали максимально простым и понятным для рядового пользователя. 

Локальный запуск:
```bash
streamlit run webapp.py
```

### Docker 
(/Docker/api.Dockerfile & /Docker/webapp/Dockerfile & docker-compose.yaml)

Для деплоя на сервер обернули api и webapp в docker-контейнеры. О них можно узнать в docker-compose.yaml. 

```bash
docker-compose up --build api webapp
```
