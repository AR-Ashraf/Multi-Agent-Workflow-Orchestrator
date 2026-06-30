# Cadenza Next.js frontend (standalone output). Build context is the REPO ROOT
# (pnpm workspace — needs packages/shared and the root lockfile).
#   docker build -f apps/web/Dockerfile -t cadenza-web .
# syntax=docker/dockerfile:1
FROM node:22-slim AS base
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH CI=1 NEXT_TELEMETRY_DISABLED=1
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
WORKDIR /app

FROM base AS build
# NEXT_PUBLIC_* are inlined into the client bundle at BUILD time (CLAUDE.md §11),
# so they must be passed as build args, not runtime env.
ARG NEXT_PUBLIC_API_BASE=""
ARG NEXT_PUBLIC_GA_ID=""
ARG NEXT_PUBLIC_GTM_ID=""
ARG NEXT_PUBLIC_BOOK_URL=""
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE \
    NEXT_PUBLIC_GA_ID=$NEXT_PUBLIC_GA_ID \
    NEXT_PUBLIC_GTM_ID=$NEXT_PUBLIC_GTM_ID \
    NEXT_PUBLIC_BOOK_URL=$NEXT_PUBLIC_BOOK_URL
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/shared ./packages/shared
COPY apps/web ./apps/web
RUN pnpm install --frozen-lockfile
RUN pnpm --filter web build

FROM base AS run
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
# Standalone bundles a minimal server + node_modules, mirroring the monorepo layout.
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /app/apps/web/public ./apps/web/public
RUN useradd -r -u 10001 cadenza && chown -R cadenza /app
USER cadenza
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
