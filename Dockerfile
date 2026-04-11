# Stage 1: Build Frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend

# Install dependencies first for better caching
COPY frontend/package*.json ./
RUN npm install

# Build compiled assets
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve Backend & Frontend
FROM python:3.11-alpine
WORKDIR /app/backend

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend logic
COPY backend/ ./

# Copy vue dist output directly into python's static folder
RUN mkdir -p static
COPY --from=frontend-build /app/frontend/dist ./static

# Ensure correct volume configurations
RUN mkdir -p /root/.config/gmail-client

# Expose internal port
EXPOSE 8000

# Execute server
ENV HOST=0.0.0.0
ENV PORT=8000
CMD ["python", "main.py"]
