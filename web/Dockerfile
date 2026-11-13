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

# Maintained Debian13 / Node24 runtime; native build and runtime share glibc.
# Complete vendor runtime closure includes CA roots and DNS support, without
# package managers or a shell. No hand-selected library deletion/copying.
FROM gcr.io/distroless/nodejs24-debian13:nonroot@sha256:6abfcb367ebc291572c774c1592a986be2ab26a2486f73093401327495a5962a AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000 PATH=/nodejs/bin:/usr/local/bin:/usr/bin:/bin
COPY --from=build --chown=1000:1000 /app/.next/standalone ./
COPY --from=build --chown=1000:1000 /app/.next/static ./.next/static
COPY --from=build --chown=1000:1000 /app/public ./public
USER 1000:1000
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=8s --start-period=30s --retries=3 CMD ["node", "-e", "fetch('http://127.0.0.1:3000/health',{signal:AbortSignal.timeout(5000)}).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
ENTRYPOINT []
CMD ["node", "server.js"]
