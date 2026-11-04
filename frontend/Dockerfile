# Build the static assets, then serve them with nginx.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# The official image renders /etc/nginx/templates/*.template with envsubst at
# startup, injecting BACKEND_ORIGIN and PORT.
COPY default.conf.template /etc/nginx/templates/default.conf.template
ENV BACKEND_ORIGIN=http://backend:8000 \
    PORT=80
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- "http://localhost:${PORT:-80}/" >/dev/null 2>&1 || exit 1
