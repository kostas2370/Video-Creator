# Two stages: node builds the bundle, nginx serves it. Node and node_modules stay in
# the builder, so the published image is the static output plus nginx — tens of MB
# rather than the couple of GB an installed node_modules takes.
FROM node:20-alpine AS builder

WORKDIR /app

# Copied first so `npm ci` is only re-run when the dependencies actually change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# CRA treats warnings as errors when CI is set, and this tree has plenty of them
# (unused imports, exhaustive-deps). They should be cleaned up, but they must not
# fail the image build.
ENV CI=false
RUN npm run build


FROM nginx:1.27-alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx's default mime.types has no entry for .wav, so the narration audio would be
# served as application/octet-stream, which <audio> is entitled to refuse. Appended
# inside the existing types block rather than declared in the server config, because a
# `types` block in a location replaces the inherited map instead of extending it.
RUN sed -i '/^}/i\    audio/wav                                        wav;' /etc/nginx/mime.types

EXPOSE 80
