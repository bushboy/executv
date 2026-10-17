FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_CORE_ENGINE_URL=http://localhost:8001
ARG VITE_INGRESS_GATEWAY_URL=http://localhost:8000
ENV VITE_CORE_ENGINE_URL=$VITE_CORE_ENGINE_URL \
    VITE_INGRESS_GATEWAY_URL=$VITE_INGRESS_GATEWAY_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
