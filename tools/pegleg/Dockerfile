FROM python:3.6

VOLUME /var/pegleg
WORKDIR /var/pegleg

COPY requirements.txt /opt/pegleg/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/pegleg/requirements.txt

COPY . /opt/pegleg
RUN pip3 install -e /opt/pegleg
