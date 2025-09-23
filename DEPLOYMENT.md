# NBA Draft Tool Deployment Guide

## Option 1: Quick Deploy to Cloud (Recommended)

### Backend - Deploy to Railway or Render

#### Railway (Easiest)
1. Create account at [railway.app](https://railway.app)
2. Install Railway CLI: `npm i -g @railway/cli`
3. Deploy backend:
```bash
cd backend
railway login
railway init
railway up
```
4. Get your backend URL from Railway dashboard

#### Render
1. Create account at [render.com](https://render.com)
2. Connect GitHub repo
3. Create new Web Service
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend - Deploy to Vercel or Netlify

#### Vercel (Recommended for React)
1. Install Vercel CLI: `npm i -g vercel`
2. Update frontend API URL:
```bash
cd frontend
# Edit src/config/api.ts to use your backend URL
```
3. Deploy:
```bash
vercel
```

#### Netlify
1. Build frontend:
```bash
cd frontend
npm run build
```
2. Drag `build` folder to [netlify.com](https://app.netlify.com/drop)

## Option 2: Self-Host with Docker

### Create Docker containers:

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 80
```

### Docker Compose:
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=http://localhost:3000

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

Run: `docker-compose up -d`

## Option 3: Deploy to VPS (DigitalOcean/AWS/Linode)

### 1. Setup Ubuntu server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and Node.js
sudo apt install python3-pip python3-venv nodejs npm nginx -y
```

### 2. Deploy Backend
```bash
# Clone repo
git clone <your-repo>
cd nba_draft/backend

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with systemd
sudo nano /etc/systemd/system/nba-backend.service
```

Add to service file:
```ini
[Unit]
Description=NBA Draft Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/nba_draft/backend
Environment="PATH=/home/ubuntu/nba_draft/backend/venv/bin"
ExecStart=/home/ubuntu/nba_draft/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nba-backend
sudo systemctl start nba-backend
```

### 3. Deploy Frontend
```bash
cd ../frontend
npm install
npm run build

# Copy to nginx
sudo cp -r build/* /var/www/html/
```

### 4. Configure Nginx
```nginx
# /etc/nginx/sites-available/default
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /var/www/html;
        try_files $uri /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## Environment Variables

### Backend (.env)
```
CORS_ORIGINS=https://your-frontend-url.com
```

### Frontend (.env.production)
```
REACT_APP_API_URL=https://your-backend-url.com
```

## Free Hosting Options

1. **Backend**:
   - Railway (500 hours/month free)
   - Render (750 hours/month free)
   - Fly.io (generous free tier)

2. **Frontend**:
   - Vercel (unlimited for personal)
   - Netlify (300 build minutes/month)
   - GitHub Pages (static only)

## Post-Deployment Checklist

- [ ] Test all API endpoints
- [ ] Verify CORS settings
- [ ] Check WebSocket connections (if any)
- [ ] Monitor error logs
- [ ] Setup domain name (optional)
- [ ] Enable HTTPS (automatic on most platforms)
- [ ] Test on mobile devices
- [ ] Setup monitoring (UptimeRobot free tier)

## Estimated Costs

- **Free Tier**: $0/month (Railway + Vercel)
- **Basic VPS**: $5-10/month (DigitalOcean droplet)
- **Production**: $20-50/month (dedicated resources)

## Quick Start Commands

```bash
# Backend local test
cd backend
python -m uvicorn main:app --reload

# Frontend local test
cd frontend
npm start

# Full deployment to Railway + Vercel
cd backend && railway up
cd ../frontend && vercel --prod
```