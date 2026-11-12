# Rehearsal-only fixture. Keep the supported Mongo 8.0 server and mongosh.
FROM mongo:8.0@sha256:d97fea17ccb8d004cd137be8dab54d70d0df11be69c9f422aefe4484c8414ab7
# Upstream entrypoint vendors this YAML helper separately under /opt/js-yaml.
# Replace it with the supported same-major security patch, verified against
# npm registry SHA512 metadata and this independently recorded SHA256.
RUN curl --fail --silent --show-error --location https://registry.npmjs.org/js-yaml/-/js-yaml-3.15.2.tgz -o /tmp/js-yaml.tgz \
    && echo '7f005cf0b8ee639b4557e0e321dc067c1f2aa0a442d096e03f2ab53353738794  /tmp/js-yaml.tgz' | sha256sum -c - \
    && tar -xzf /tmp/js-yaml.tgz -C /tmp package/dist/js-yaml.js package/package.json \
    && cp /tmp/package/dist/js-yaml.js /opt/js-yaml/js-yaml.js \
    && cp /tmp/package/package.json /opt/js-yaml/package.json \
    && rm -rf /tmp/package /tmp/js-yaml.tgz
USER 999:999
