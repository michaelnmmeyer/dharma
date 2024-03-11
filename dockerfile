FROM debian:stable-slim
RUN apt-get update && \
	apt-get upgrade -y && \
	apt-get install -y apt-utils && \
	apt-get install -y git && \
	apt-get install -y rsync && \
	apt-get install -y python3-minimal python3-requests python3-icu && \
	apt-get install -y python3-pip && \
	apt-get clean && \
	pip3 install saxonche --break-system-packages && \
	pip3 install websockets --break-system-packages && \
	pip3 install Jinja2 --break-system-packages && \
	apt-get clean -y && \
	git config --global --add safe.directory '*' && \
	git config --global user.email michaelnm.meyer@gmail.com && \
	git config --global user.name "Michaël Meyer" && \
	mkdir /root/.ssh && \
	ssh-keyscan -H github.com >> /root/.ssh/known_hosts && \
	test -f /usr/share/zoneinfo/Europe/Paris && \
	ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime
COPY ssh_key /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa
ENV PYTHONPATH=$PYTHONPATH:/
ENV WITHIN_DOCKER=1
ENV DHARMA_HOME=/dharma
ADD . $DHARMA_HOME
WORKDIR $DHARMA_HOME
EXPOSE 8023
CMD bash run.sh
