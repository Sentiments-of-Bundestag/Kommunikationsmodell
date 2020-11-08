FROM python:3.8.6-slim

ADD ./ /tmp/cme

RUN cd /tmp/cme \
    && pip3 install --no-cache-dir .

RUN rm -r /tmp/cme

CMD cme server