FROM python:3.6

VOLUME /var/pegleg
WORKDIR /var/pegleg

ARG ctx_base=src/bin/pegleg

COPY ${ctx_base}/requirements.txt /opt/pegleg/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/pegleg/requirements.txt

COPY ${ctx_base} /opt/pegleg
RUN pip3 install -e /opt/pegleg
