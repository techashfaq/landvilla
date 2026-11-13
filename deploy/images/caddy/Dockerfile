# Custom stable-core candidate using the coherent dependency updates accepted
# upstream in PR8368. Do not pull the 125 unrelated master commits into runtime.
FROM caddy:2.11.9-builder-alpine@sha256:646fee578e680989ca5c7fd1ce6f1de574d19fd71ef2221810cc0510a9f40c86 AS builder
ENV CGO_ENABLED=0 GOTOOLCHAIN=local
RUN git init /src && cd /src \
    && git remote add origin https://github.com/caddyserver/caddy.git \
    && git fetch --depth=1 origin 0d98caea58f794f88e709b1bef2880996a471bca \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = 0d98caea58f794f88e709b1bef2880996a471bca \
    && go get github.com/smallstep/certificates@v0.30.3-0.20261105213751-6d5a251fbe01 \
        go.step.sm/crypto@v0.92.0 github.com/klauspost/compress@v1.20.3 golang.org/x/net@v0.62.0 \
    && go mod tidy \
    && go test -count=1 ./caddyconfig/... ./modules/caddyhttp/... ./modules/caddytls/...
# xcaddy is upstream's custom builder. Retain the stable Caddy module version
# and standard modules; no direct go-jose major replacement or custom plugins.
RUN mkdir /xcaddy-temp \
    && XCADDY_SKIP_CLEANUP=1 TMPDIR=/xcaddy-temp xcaddy build v2.11.9 --output /usr/bin/caddy \
    --replace github.com/smallstep/certificates=github.com/smallstep/certificates@v0.30.3-0.20261105213751-6d5a251fbe01 \
    --replace go.step.sm/crypto=go.step.sm/crypto@v0.92.0 \
    --replace github.com/klauspost/compress=github.com/klauspost/compress@v1.20.3 \
    --replace golang.org/x/net=golang.org/x/net@v0.62.0 \
    && set -- /xcaddy-temp/buildenv_* && test "$#" -eq 1 && cd "$1" \
    && go mod download all \
    && sha256sum go.mod go.sum > /tmp/tested-module-graph.sha256 \
    && go test -mod=readonly -count=1 -tags=nobadger,nomysql,nopgx \
        github.com/caddyserver/caddy/v2/caddyconfig/... \
        github.com/caddyserver/caddy/v2/modules/caddyhttp/... \
        github.com/caddyserver/caddy/v2/modules/caddytls/... \
    && sha256sum -c /tmp/tested-module-graph.sha256 \
    && go list -m all && go version -m /usr/bin/caddy

# Security candidate only. Production Compose/Caddy settings are unchanged.
FROM caddy:2.11.9-alpine@sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee
RUN apk add --no-cache --upgrade zlib=1.4-r0
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
LABEL org.landvilla.caddy.core=0d98caea58f794f88e709b1bef2880996a471bca \
      org.landvilla.caddy.dependency-review=31f9f0cb99491fdd1a27f82793b78d216c5b2a76
USER 10001:10001
