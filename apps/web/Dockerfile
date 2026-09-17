FROM node:22-alpine AS build

ARG VITE_DEV_ROLE=analyst
ARG VITE_DEMO_LABEL=""
ARG VITE_AUTH_MODE=production
ENV VITE_DEV_ROLE=$VITE_DEV_ROLE \
    VITE_DEMO_LABEL=$VITE_DEMO_LABEL \
    VITE_AUTH_MODE=$VITE_AUTH_MODE

RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
ENV API_UPSTREAM=http://api:8000 \
    NGINX_ENVSUBST_FILTER=API_UPSTREAM
COPY deploy/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=755 deploy/15-create-demo-auth.sh /docker-entrypoint.d/15-create-demo-auth.sh
EXPOSE 8080
