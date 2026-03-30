FROM debian:trixie

RUN apt-get update && apt-get install -y \
    iw \
    wireless-tools \
    net-tools \
    iproute2 \
    vnstat \
    ifstat \
    mtr-tiny \
    dnsutils \
    iputils-ping \
    curl \
    speedtest-cli \
    && apt-get clean

COPY monitor.sh /monitor.sh
RUN chmod +x /monitor.sh

CMD ["/monitor.sh"]
