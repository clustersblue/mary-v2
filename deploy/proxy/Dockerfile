FROM nginx:stable-alpine

RUN apk add --no-cache openssl \
    && rm -f /etc/nginx/conf.d/default.conf

COPY nginx/prod.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/proxy_params.conf /etc/nginx/proxy_params.conf
COPY proxy/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod 0755 /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
