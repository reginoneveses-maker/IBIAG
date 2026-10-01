FROM node:20-alpine AS build
WORKDIR /app

COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

COPY frontend/ ./
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["sh", "-c", "envsubst '\$PORT' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
