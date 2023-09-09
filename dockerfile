FROM debian:12-slim
RUN apt-get update && \
	apt-get upgrade -y && \
	apt-get install -y openjdk-17-jdk-headless && \
	apt-get install -y git && \
	apt-get install -y python3-minimal python3-bs4 python3-requests python3-icu && \
	apt-get clean -y && \
	git config --global --add safe.directory '*' && \
	mkdir /root/.ssh && \
	ssh-keyscan -H github.com >> /root/.ssh/known_hosts && \
	timedatectl set-timezone Europe/Paris
COPY ssh_key /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa
ENV PYTHONPATH=$PYTHONPATH:/
ENV WITHIN_DOCKER=1
ENV DHARMA_HOME=/dharma
ADD . $DHARMA_HOME
WORKDIR $DHARMA_HOME
EXPOSE 8023
CMD bash run.sh
