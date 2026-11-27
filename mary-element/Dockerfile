FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
ENV NODE_OPTIONS=--max-old-space-size=1536
RUN npm run build

FROM nginx:stable-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

RUN nginx -t

USER nginx
EXPOSE 8080
STOPSIGNAL SIGQUIT
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
