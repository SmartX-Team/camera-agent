FROM nginx:alpine

RUN apk add --no-cache gettext

COPY nginx.conf /etc/nginx/nginx.conf

COPY src/index.html /usr/share/nginx/html/
COPY src/styles.css /usr/share/nginx/html/
COPY src/main.js.template /usr/share/nginx/html/

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8111

CMD ["nginx", "-g", "daemon off;"]