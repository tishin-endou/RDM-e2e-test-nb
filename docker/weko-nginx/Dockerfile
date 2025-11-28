FROM ubuntu:focal

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nginx \
    openssl

RUN rm -f /etc/nginx/conf.d/default.conf /etc/nginx/nginx.conf
ADD weko.conf /etc/nginx/conf.d/
ADD nginx.conf /etc/nginx/nginx.conf
ADD ./keys/server.crt /etc/nginx/server.crt
ADD ./keys/server.key /etc/nginx/server.key
RUN chmod 400 /etc/nginx/server.key

ADD redirect_list.map /etc/nginx/redirect_list.map

CMD ["nginx", "-g", "daemon off;"]
