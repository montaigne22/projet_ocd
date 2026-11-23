# syntax=docker/dockerfile:1.7
#
# FreeSWITCH for the WhatsApp calls of OCD, built from its sources (free, no account needed),
# with only the modules the calls use. Build context: whatsapp_cloud_call/freeswitch.
#
#   docker compose build      (see docker/docker-compose.yml)
#
# The configuration of OCD (conf/, scripts/) is in the image; the entrypoint puts it together
# with the settings of the environment at each start (docker/entrypoint.sh).
ARG DEBIAN_IMAGE=debian:bookworm-20261104-slim

# ---------------------------------------------------------------------------------------------
FROM ${DEBIAN_IMAGE} AS build
ARG FREESWITCH_REF=v1.11.3
ARG SOFIA_SIP_REF=v1.13.19
ARG SPANDSP_REF=v3.1.1
ARG MUSIC_VERSION=1.0.52
ENV DEBIAN_FRONTEND=noninteractive
COPY docker/build_ca.sh /usr/local/bin/build_ca.sh

RUN --mount=type=secret,id=build_ca,required=false \
    . /usr/local/bin/build_ca.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential autoconf automake libtool libtool-bin pkg-config git ca-certificates curl \
        libssl-dev libcurl4-openssl-dev libpcre2-dev libspeex-dev libspeexdsp-dev libsqlite3-dev \
        libedit-dev libopus-dev libsndfile1-dev liblua5.3-dev uuid-dev zlib1g-dev libtiff-dev \
        libjpeg-dev

WORKDIR /usr/src
RUN --mount=type=secret,id=build_ca,required=false \
    . /usr/local/bin/build_ca.sh \
    && git clone --depth 1 --branch "${SPANDSP_REF}" https://github.com/freeswitch/spandsp.git \
    && git clone --depth 1 --branch "${SOFIA_SIP_REF}" https://github.com/freeswitch/sofia-sip.git \
    && git clone --depth 1 --branch "${FREESWITCH_REF}" https://github.com/signalwire/freeswitch.git \
    && curl -fsSL -o music.tar.gz \
        "https://files.freeswitch.org/releases/sounds/freeswitch-sounds-music-16000-${MUSIC_VERSION}.tar.gz"

# installed in / to build FreeSWITCH, and in /opt/stage for the final image
RUN cd spandsp && ./bootstrap.sh && ./configure --prefix=/usr --disable-static \
    && make -j"$(nproc)" && make install && make install DESTDIR=/opt/stage
RUN cd sofia-sip && ./bootstrap.sh && ./configure --prefix=/usr --disable-static --with-glib=no \
        --without-doxygen --disable-stun \
    && make -j"$(nproc)" && make install && make install DESTDIR=/opt/stage

COPY docker/modules.conf /usr/src/freeswitch/modules.conf
RUN cd freeswitch && ./bootstrap.sh -j \
    && ./configure --prefix=/usr --localstatedir=/var --sysconfdir=/etc --enable-fhs \
        --disable-libvpx --disable-libyuv --disable-core-odbc-support --disable-dependency-tracking \
    && make -j"$(nproc)" \
    && make install DESTDIR=/opt/stage \
    && mkdir -p /opt/stage/usr/share/freeswitch/conf \
    && cp -r conf/vanilla /opt/stage/usr/share/freeswitch/conf/vanilla \
    && mkdir -p /opt/stage/usr/share/freeswitch/sounds \
    && tar -xzf /usr/src/music.tar.gz -C /opt/stage/usr/share/freeswitch/sounds \
    && rm -rf /opt/stage/var/run /opt/stage/usr/include /opt/stage/usr/lib/pkgconfig /opt/stage/usr/lib/*.la \
        /opt/stage/usr/lib/freeswitch/mod/*.la /opt/stage/usr/share/man

# ---------------------------------------------------------------------------------------------
FROM ${DEBIAN_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive
COPY docker/build_ca.sh /usr/local/bin/build_ca.sh
RUN --mount=type=secret,id=build_ca,required=false \
    . /usr/local/bin/build_ca.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl openssl tini libssl3 libcurl4 libpcre2-8-0 libspeex1 libspeexdsp1 \
        libsqlite3-0 libedit2 libopus0 libsndfile1 liblua5.3-0 libuuid1 zlib1g libtiff6 \
        libjpeg62-turbo \
        # the recorded messages of the team given in MP3, decoded at each start (entrypoint)
        mpg123 \
    && build_ca_done \
    && rm -rf /var/lib/apt/lists/* \
    # a fixed user, the same in the other containers that share the files of FreeSWITCH
    && groupadd --system --gid 4999 freeswitch \
    && useradd --system --uid 4999 --gid 4999 --home-dir /var/lib/freeswitch --shell /usr/sbin/nologin freeswitch

COPY --from=build /opt/stage/ /
RUN ldconfig \
    && freeswitch -version \
    # every module finds its libraries
    && ! (for module in /usr/lib/freeswitch/mod/*.so /usr/bin/freeswitch; do ldd "$module"; done | grep "not found")

# the configuration of OCD, put together at each start
COPY conf /usr/share/ocd/conf
COPY scripts /usr/share/ocd/scripts
COPY docker/entrypoint.sh /usr/local/bin/ocd-freeswitch-entrypoint
COPY docker/healthcheck.sh /usr/local/bin/ocd-freeswitch-healthcheck
RUN chmod 755 /usr/local/bin/ocd-freeswitch-entrypoint /usr/local/bin/ocd-freeswitch-healthcheck \
    && mkdir -p /etc/freeswitch /var/lib/freeswitch/ocd /var/log/freeswitch /var/spool/ocd-calls \
        /usr/share/freeswitch/sounds/ocd /run/freeswitch

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/local/bin/ocd-freeswitch-healthcheck"]
STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/ocd-freeswitch-entrypoint"]
