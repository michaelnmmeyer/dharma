FROM debian:12
RUN apt-get update && \
	apt-get install python3-minimal openjdk-17-jdk-headless python3-bs4 git -y && \
	apt-get clean -y
ADD . /dharma
WORKDIR /dharma
#EXPOSE 8023
CMD PYTHONPATH=$PYTHONPATH:/ python3 server.py
