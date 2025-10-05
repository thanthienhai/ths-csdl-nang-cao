FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Set Node.js options for compatibility with older Webpack
ENV NODE_OPTIONS="--openssl-legacy-provider"

# Expose port
EXPOSE 3000

# Start the development server
CMD ["npm", "start"]