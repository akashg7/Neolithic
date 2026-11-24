# Web app (React Native Web) built once, served by nginx, which also proxies
# /api to the FastAPI container. Same origin → no CORS, no API host baked in.
FROM node:20-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN NODE_ENV=production npm run build

FROM nginx:1.28-alpine
COPY --from=build /web/dist /usr/share/nginx/html
# Config is mounted from the repo (deploy/nginx.conf) by docker-compose.
EXPOSE 80
