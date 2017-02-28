FROM python:2.7

COPY app.py /root/app.py
COPY requirements.txt /root/requirements.txt
RUN pip install -r /root/requirements.txt
CMD [ "python", "/root/app.py" ]
EXPOSE 5000
