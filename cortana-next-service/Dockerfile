# Base image
FROM node:20-alpine

# Create app directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the app
COPY . .

# Expose port
EXPOSE 3000

# Dev entrypoint
CMD ["npm", "run", "dev"]
