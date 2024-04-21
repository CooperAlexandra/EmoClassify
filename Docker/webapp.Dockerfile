FROM api:0.0.1

WORKDIR /emotionrecognition

COPY webapp.py /emotionrecognition/

EXPOSE 8501
CMD ["streamlit", "run", "webapp.py"]