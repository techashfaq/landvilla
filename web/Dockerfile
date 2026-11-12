# Build on the deployment target architecture; never copy local node_modules.
FROM node:24-trixie-slim@sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0 AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:24-trixie-slim@sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0 AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID=""
ENV NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID}
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
# Public configuration only, used for build metadata. Runtime config is supplied
# by Compose. No database/storage secrets or environment files enter the image.
ENV WEB_ORIGIN=https://landvilla.in BACKEND_ORIGIN=http://api:8000 BACKEND_TRANSPORT=private-http
RUN mkdir -p public && npm run build

FROM node:24-trixie-slim@sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0 AS runtime
# Apply the signed Trixie security fix. The standalone server invokes node
# directly; npm/npx and Yarn are build tooling, not runtime dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 \
    && rm -rf /var/lib/apt/lists/* /usr/local/lib/node_modules/npm /opt/yarn-* \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/yarn /usr/local/bin/yarnpkg
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=8s --start-period=30s --retries=3 CMD ["node", "-e", "fetch('http://127.0.0.1:3000/health',{signal:AbortSignal.timeout(5000)}).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "server.js"]
