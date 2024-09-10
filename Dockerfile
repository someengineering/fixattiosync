FROM fedora:40 AS build-env
ENV LANG="C.UTF-8"
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TESTS
ARG SOURCE_COMMIT

ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
RUN echo "I am running on ${BUILDPLATFORM}, building for ${TARGETPLATFORM}"

WORKDIR /
RUN dnf -y update \
    && dnf -y groupinstall "Development Tools" "Development Libraries" \
    && dnf -y install \
        gcc \
        python3-devel \
        python3-pip \
        shellcheck \
        curl \
        ca-certificates \
        dateutils \
        openssl \
        openssl-devel \
        rustc \
        cargo \
        git

# Create CPython venv
WORKDIR /usr/local
RUN python3 -m venv fix-venv-python3

# Download and install Python test tools
RUN . /usr/local/fix-venv-python3/bin/activate && python -m pip install -U pip wheel tox flake8

# Build Fix Inventory
COPY . /usr/src/fixattiosync

WORKDIR /usr/src/fixattiosync
RUN . /usr/local/fix-venv-python3/bin/activate && pip install -r requirements.txt
RUN . /usr/local/fix-venv-python3/bin/activate && python -m pip install .

COPY bootstrap /usr/local/sbin/bootstrap
RUN chmod 755 \
    /usr/local/sbin/bootstrap
RUN echo "${SOURCE_COMMIT:-unknown}" > /usr/local/etc/git-commit.HEAD


# Setup main image
FROM fedora:40
ENV LANG="C.UTF-8"
ENV TERM="xterm-256color"
ENV COLORTERM="truecolor"
ENV EDITOR="vim"
COPY --from=build-env /usr/local /usr/local
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
WORKDIR /
RUN groupadd -g "${PGID:-0}" -o fix \
    && useradd -g "${PGID:-0}" -u "${PUID:-0}" -o --create-home fix \
    && dnf -y update \
    && dnf -y install \
        dumb-init \
        python3 \
        python3-pip \
        iproute \
        libffi \
        openssl \
        procps \
        dateutils \
        curl \
        ca-certificates \
    && dnf clean all \
    && rm -rf /var/cache/dnf /tmp/* /var/tmp/*

ENTRYPOINT ["/bin/dumb-init", "--", "/usr/local/sbin/bootstrap"]
CMD ["/bin/bash"]
