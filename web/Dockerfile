# Build on the deployment target architecture; never copy local node_modules.
FROM node:24-bookworm-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:24-bookworm-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS build
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

FROM node:24-bookworm-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=8s --start-period=30s --retries=3 CMD ["node", "-e", "fetch('http://127.0.0.1:3000/health',{signal:AbortSignal.timeout(5000)}).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "server.js"]
