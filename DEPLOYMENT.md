# 🚀 Deployment Guide - Mountaineering Club Platform

This guide covers deploying your mountaineering club web platform to production.

## 📋 Prerequisites

Before deployment, you'll need:

- ✅ **GitHub repository** with your code
- ✅ **MongoDB Atlas account** (free tier available)
- ✅ **AWS account** for S3 image storage
- ✅ **Railway account** (recommended) or DigitalOcean
- ✅ **Google/Facebook Developer accounts** (for OAuth)

---

## 🔧 Step 1: Pre-Deployment Configuration

### 1.1 Generate Production Secret Key
```bash
python generate_secret_key.py
# Copy one of the generated keys for SECRET_KEY
```

### 1.2 Set up MongoDB Atlas
1. Go to [MongoDB Atlas](https://cloud.mongodb.com/)
2. Create free cluster
3. Create database user
4. Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/mountaineering_club`

### 1.3 Configure AWS S3
1. Create S3 bucket: `your-club-name-images`
2. Create IAM user with S3 permissions
3. Get Access Key ID and Secret Access Key
4. (Optional) Set up CloudFront for faster image delivery

### 1.4 Validate Configuration
```bash
# Test your configuration
python check_config.py
```

---

## 🚂 Step 2: Railway Deployment (Recommended)

### 2.1 Deploy to Railway
1. Go to [Railway.app](https://railway.app/)
2. Connect your GitHub repository
3. Deploy from `main` branch

### 2.2 Configure Environment Variables
In Railway dashboard, add these variables:

```bash
# Core Configuration
SECRET_KEY=your-64-char-secret-key-from-generator
FLASK_ENV=production
DEBUG=False

# Database
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/mountaineering_club

# AWS S3 Storage
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=eu-central-1

# OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-secret
FACEBOOK_CLIENT_ID=your-facebook-app-id
FACEBOOK_CLIENT_SECRET=your-facebook-secret

# Email (Optional)
EMAIL_USER=your-club-email@gmail.com
EMAIL_PASS=your-app-password
```

### 2.3 Update OAuth Redirect URIs
Update your OAuth applications:
- **Google**: `https://your-app.railway.app/auth/google/callback`
- **Facebook**: `https://your-app.railway.app/auth/facebook/callback`

---

## 🌊 Alternative: DigitalOcean App Platform

### Deploy to DigitalOcean
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Create new app from GitHub
3. Configure same environment variables as Railway
4. Deploy

---

## 👑 Step 3: Create First Admin User

After successful deployment:

### 3.1 Access Railway Console
```bash
# In Railway dashboard, open console and run:
python create_admin.py
```

### 3.2 Follow Interactive Prompts
```
Admin email: admin@your-club.si
Admin full name: Club Administrator  
Admin password: [secure password]
Confirm password: [same password]
```

---

## ✅ Step 4: Post-Deployment Verification

### 4.1 Test Health Check
```bash
curl https://your-app.railway.app/health
# Should return: {"status": "healthy", "database": "connected"}
```

### 4.2 Test Admin Login
1. Go to `https://your-app.railway.app/login`
2. Login with admin credentials
3. Access admin panel: `https://your-app.railway.app/admin`

### 4.3 Test Core Features
- ✅ User registration and approval
- ✅ Trip report creation with images
- ✅ Comments system
- ✅ Trip planning and RSVP
- ✅ OAuth login (if configured)

---

## 🔒 Security Checklist

Before going live:

- ✅ SECRET_KEY is 64+ characters and unique
- ✅ DEBUG=False in production
- ✅ MongoDB connection uses strong password
- ✅ AWS S3 bucket has proper permissions
- ✅ OAuth redirect URIs are HTTPS
- ✅ Admin user created with strong password

---

## 📊 Monitoring & Maintenance

### Health Monitoring
- Railway provides automatic health checks via `/health` endpoint
- Monitor logs in Railway/DigitalOcean dashboard

### Database Backups
- MongoDB Atlas provides automatic backups
- Download periodic backups for extra safety

### Cost Management
- **Railway**: ~$5/month
- **MongoDB Atlas**: Free tier (512MB)
- **AWS S3**: ~$1-5/month depending on image storage

---

## 🆘 Troubleshooting

### Common Issues

**"Application failed to start"**
- Check environment variables are set correctly
- Verify MongoDB connection string
- Check Railway logs for specific errors

**"Database connection failed"**
- Verify MongoDB Atlas IP whitelist (use 0.0.0.0/0 for Railway)
- Check username/password in connection string
- Ensure database user has read/write permissions

**"Images not uploading"**
- Verify AWS credentials and bucket name
- Check S3 bucket permissions
- Ensure bucket is in correct region

**"OAuth not working"**
- Verify redirect URIs match exactly (including HTTPS)
- Check client ID/secret are correct
- Ensure OAuth apps are published/approved

---

## 🎉 Success!

Your mountaineering club platform is now live! 

**Next Steps:**
- Share login URL with club members
- Configure email notifications
- Add custom domain (optional)
- Set up Redis for enhanced performance (optional)

**Support:** Check Railway/DigitalOcean documentation for platform-specific help.