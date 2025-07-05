# Mountaineering Club Web Platform

A private web platform for mountaineering club members to connect, share experiences, and plan adventures.

## Features

### Phase 1 (MVP)
- ✅ Home page with club information
- ✅ Member authentication system with admin approval
- ✅ Real-time announcements
- ✅ Trip reports with photo uploads
- ✅ Group chat functionality
- ✅ Basic member profiles

### Phase 2 (Planned)
- Trip planning with weather integration
- Gear checklist templates
- RSVP system for trips
- Achievement badges
- Climbing resume tracker
- Member photo galleries

## Technology Stack

- **Backend**: Python + Flask
- **Database**: MongoDB
- **Frontend**: HTML/CSS/JavaScript (Bootstrap 5)
- **Real-time**: WebSockets (chat) + Server-Sent Events (announcements)
- **Image Management**: Cloudinary
- **Caching**: Redis

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd mountaineering-club
   cp .env.example .env
   ```

2. **Configure environment variables** in `.env`:
   ```bash
   # Required for basic functionality
   SECRET_KEY=your-secret-key-here
   
   # Required for image uploads
   CLOUDINARY_CLOUD_NAME=your-cloud-name
   CLOUDINARY_API_KEY=your-api-key
   CLOUDINARY_API_SECRET=your-api-secret
   
   # Optional for weather features
   OPENWEATHER_API_KEY=your-weather-api-key
   
   # Optional for email notifications
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASS=your-email-password
   ```

3. **Run with Docker**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Web app: http://localhost:5000
   - MongoDB: localhost:27017
   - Redis: localhost:6379

### Local Development

1. **Setup Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start services**:
   ```bash
   # Start MongoDB (install separately)
   mongod
   
   # Start Redis (install separately)
   redis-server
   
   # Start Flask app
   python app.py
   ```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask secret key for sessions |
| `MONGO_URI` | No | MongoDB connection string (default: localhost) |
| `REDIS_HOST` | No | Redis host (default: localhost) |
| `CLOUDINARY_CLOUD_NAME` | Yes | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Yes | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Yes | Cloudinary API secret |
| `OPENWEATHER_API_KEY` | No | OpenWeatherMap API key |
| `EMAIL_USER` | No | Email for notifications |
| `EMAIL_PASS` | No | Email password |

### First Admin User

After deployment, you'll need to manually set the first admin user in MongoDB:

```javascript
db.users.updateOne(
    { email: "admin@example.com" },
    { 
        $set: { 
            is_admin: true, 
            is_approved: true 
        } 
    }
)
```

## API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /login` - User login
- `GET /logout` - User logout

### Main Pages
- `GET /` - Home page
- `GET /dashboard` - Member dashboard

### Real-time Features
- WebSocket `/socket.io/` - Chat functionality
- Server-Sent Events - Announcements (coming soon)

## File Upload Limits

- **Photos**: 10MB per image
- **Total per trip report**: 50MB
- **Profile photos**: 2MB

## Deployment

### Heroku

1. **Create Heroku app**:
   ```bash
   heroku create your-app-name
   ```

2. **Add MongoDB Atlas**:
   ```bash
   heroku addons:create mongolab:sandbox
   ```

3. **Add Redis**:
   ```bash
   heroku addons:create heroku-redis:hobby-dev
   ```

4. **Set environment variables**:
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set CLOUDINARY_CLOUD_NAME=your-cloud-name
   # ... other variables
   ```

5. **Deploy**:
   ```bash
   git push heroku main
   ```

### DigitalOcean/AWS

1. **Setup server with Docker**
2. **Configure environment variables**
3. **Run with docker-compose**
4. **Setup reverse proxy (nginx)**
5. **Enable SSL (Let's Encrypt)**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is private and intended for club use only.

## Support

For questions or issues, contact the development team or create an issue in the repository.