# Build stage
FROM node:14 as build
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy project files
COPY . ./

# Debug: List contents of src directory
RUN ls -la src/

# Debug: Cat important files
RUN cat src/index.js || echo "src/index.js does not exist"
RUN cat src/App.js || echo "src/App.js does not exist"
RUN cat src/App.css || echo "src/App.css does not exist"
RUN cat src/index.css || echo "src/index.css does not exist"
RUN cat tailwind.config.js || echo "tailwind.config.js does not exist"

# Build the project
RUN npm run build

# Production stage
FROM nginx:stable-alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 3000

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]