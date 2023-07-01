FROM debian:12-slim
RUN apt-get update && \
	apt-get install --no-install-recommends -y openjdk-17-jdk-headless&& \
	apt-get install --no-install-recommends -y git && \
	apt-get install --no-install-recommends -y python3-minimal python3-bs4 python3-requests && \
	apt-get clean -y && \
	echo 'echo all > /dharma/repos/change.hid' > /etc/cron.daily/dharma-update && \
	chmod +x /etc/cron.daily/dharma-update
ENV PYTHONPATH=$PYTHONPATH:/
ENV WITHIN_DOCKER=1
ADD . /dharma
WORKDIR /dharma
EXPOSE 8023
CMD bash run.sh
