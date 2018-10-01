ARG FROM=python:3.6
FROM ${FROM}

LABEL org.opencontainers.image.authors='airship-discuss@lists.airshipit.org, irc://#airshipit@freenode'
LABEL org.opencontainers.image.url='https://airshipit.org'
LABEL org.opencontainers.image.documentation='https://airship-pegleg.readthedocs.org'
LABEL org.opencontainers.image.source='https://git.openstack.org/openstack/airship-pegleg'
LABEL org.opencontainers.image.vendor='The Airship Authors'
LABEL org.opencontainers.image.licenses='Apache-2.0'

VOLUME /var/pegleg
WORKDIR /var/pegleg

COPY requirements.txt /opt/pegleg/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/pegleg/requirements.txt

COPY . /opt/pegleg
RUN pip3 install -e /opt/pegleg
