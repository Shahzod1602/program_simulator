FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 nodejs ruby sqlite3 gcc g++ default-jdk-headless golang-go ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd -u 10001 -m student && mkdir /work && chown student:student /work
COPY guest.py /opt/campus/guest.py
# Warm the standard Go cache so student compilations do not need internet or persistent caches.
RUN mkdir -p /opt/go-cache && printf 'package main\nimport "fmt"\nfunc main(){fmt.Println("ready")}\n' > /tmp/warm.go && GOCACHE=/opt/go-cache go build -o /tmp/warm /tmp/warm.go && chmod -R a+rX /opt/go-cache && rm /tmp/warm /tmp/warm.go
ENV HOME=/tmp GOCACHE=/tmp/go-cache GOPATH=/tmp/go GOPROXY=off GOTOOLCHAIN=local GOMAXPROCS=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
WORKDIR /work
ENTRYPOINT ["python3", "-I", "/opt/campus/guest.py"]
