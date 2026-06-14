FROM node:22-alpine AS base
WORKDIR /app

FROM base AS deps
COPY package.json ./
RUN npm install --legacy-peer-deps

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_TILE_URL=/tiles/species/landscape/v20260614
ARG NEXT_PUBLIC_TILE_VERSION=v20260614
ARG NEXT_PUBLIC_TAXON_ROLLUPS_URL=/staged/06_taxon_rollups.tsv
ENV NEXT_PUBLIC_TILE_URL=$NEXT_PUBLIC_TILE_URL
ENV NEXT_PUBLIC_TILE_VERSION=$NEXT_PUBLIC_TILE_VERSION
ENV NEXT_PUBLIC_TAXON_ROLLUPS_URL=$NEXT_PUBLIC_TAXON_ROLLUPS_URL
RUN npm run build

FROM base AS runner
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
