FROM oven/bun:1 AS build

WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf.template
COPY nginx-entrypoint.sh /usr/local/bin/exan-nginx-entrypoint
RUN chmod +x /usr/local/bin/exan-nginx-entrypoint

ENTRYPOINT ["/usr/local/bin/exan-nginx-entrypoint"]
CMD ["nginx", "-g", "daemon off;"]

EXPOSE 80
