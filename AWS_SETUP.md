# AWS S3 Setup for Image Hosting

## Quick Setup Guide

### 1. Create AWS Account
- Go to https://aws.amazon.com
- Sign up for free account
- **Free tier includes:** 5GB S3 storage, 20,000 GET requests, 2,000 PUT requests per month

### 2. Create S3 Bucket
1. **Go to S3 Console:** https://s3.console.aws.amazon.com
2. **Click "Create bucket"**
3. **Bucket settings:**
   - **Name:** `your-club-photos` (must be globally unique)
   - **Region:** `eu-central-1` (Frankfurt - closest to Slovenia)
   - **Block public access:** UNCHECK "Block all public access"
   - **Acknowledge** the warning about public access
4. **Click "Create bucket"**

### 3. Configure Bucket Policy
1. **Go to your bucket → Permissions → Bucket policy**
2. **Add this policy** (replace `your-club-photos` with your bucket name):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-club-photos/*"
        }
    ]
}
```

### 4. Create IAM User for App
1. **Go to IAM Console:** https://console.aws.amazon.com/iam
2. **Users → Create user**
3. **Username:** `mountaineering-club-app`
4. **Attach policies:** Create custom policy with this JSON:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-club-photos/*"
        }
    ]
}
```

5. **Create access key:** Security credentials → Create access key
6. **Save:** Access key ID and Secret access key

### 5. Update .env File
```bash
AWS_ACCESS_KEY_ID=AKIA...your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-club-photos
AWS_REGION=eu-central-1
```

### 6. Test the Setup
```bash
# Install new dependencies
pip install boto3 Pillow

# Test image upload
python app.py
# Go to http://localhost:5002/trip-reports/create
# Upload a photo - should work!
```

## Cost Estimation

### AWS Free Tier (12 months):
- **5GB storage:** ~500-1000 photos
- **20,000 GET requests:** ~20,000 photo views
- **2,000 PUT requests:** ~2,000 photo uploads
- **Cost:** $0/month

### After Free Tier:
- **Storage:** $0.023/GB/month (~$2.30 for 100GB)
- **Requests:** $0.0004 per 1,000 GET, $0.005 per 1,000 PUT
- **Data transfer:** $0.09/GB (first 1GB free)
- **Total for active club:** ~$5-15/month

### Comparison:
- **Cloudinary:** $99/month after free tier
- **AWS S3:** $5-15/month for same usage
- **Savings:** $80-90/month! 💰

## Optional: CloudFront CDN
For faster worldwide delivery:
1. **Create CloudFront distribution**
2. **Origin:** Your S3 bucket
3. **Update .env:** `AWS_CLOUDFRONT_DOMAIN=d123456.cloudfront.net`
4. **Cost:** ~$1-5/month additional

## Security Notes
- ✅ **Bucket is public** for photo viewing
- ✅ **IAM user** has minimal permissions
- ✅ **Access keys** are environment variables only
- ✅ **No sensitive data** in photos folder