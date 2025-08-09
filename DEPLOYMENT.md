# Deployment Guide for Weight Certificate PDF to JSON Converter

## 🚀 Streamlit Community Cloud (Recommended)

### Step 1: Prepare Your Repository

1. **Create a GitHub repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Weight Certificate PDF to JSON Converter"
   git branch -M main
   git remote add origin https://github.com/yourusername/calJson.git
   git push -u origin main
   ```

2. **Ensure these files are included**:
   - ✅ `app.py` (main Streamlit app)
   - ✅ `weight_certificate_processor.py` (OCR processing)
   - ✅ `requirements.txt` (Python dependencies)
   - ✅ `packages.txt` (system dependencies for cloud)
   - ✅ `weight_certificate_import_schema.json` (validation schema)
   - ✅ `README.md` (documentation)

### Step 2: Deploy to Streamlit Community Cloud

1. **Go to Streamlit Community Cloud**:
   - Visit: https://share.streamlit.io/
   - Sign in with your GitHub account

2. **Create new app**:
   - Click "New app"
   - Repository: `yourusername/calJson`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL (optional): `your-app-name`

3. **Deploy**:
   - Click "Deploy!"
   - Wait for deployment (usually 2-5 minutes)

### Step 3: Your App is Live!

Your app will be available at:
`https://your-app-name.streamlit.app/`

## 🔧 Alternative Deployment Options

### Option 2: Heroku

1. **Install Heroku CLI**
2. **Create Procfile**:
   ```
   web: sh setup.sh && streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```
3. **Create setup.sh**:
   ```bash
   mkdir -p ~/.streamlit/
   echo "[server]
   port = $PORT
   enableCORS = false
   headless = true
   [theme]
   primaryColor = '#1f77b4'
   backgroundColor = '#ffffff'
   secondaryBackgroundColor = '#f0f2f6'
   textColor = '#262730'
   " > ~/.streamlit/config.toml
   ```

### Option 3: Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Option 4: Railway

1. Connect your GitHub repository
2. Railway will auto-detect Streamlit
3. Add environment variables if needed

## 📋 Deployment Checklist

Before deploying, ensure:

- [ ] All files are committed to Git
- [ ] `requirements.txt` includes all dependencies
- [ ] `packages.txt` includes system dependencies
- [ ] App works locally with `streamlit run app.py`
- [ ] No hardcoded local paths (we've made this cloud-compatible)
- [ ] Sensitive data is handled via environment variables

## 🌍 Post-Deployment

### Custom Domain (Optional)
- Most platforms allow custom domain setup
- Configure DNS CNAME to point to your app URL

### Monitoring
- Streamlit Community Cloud provides basic analytics
- Monitor app performance and usage

### Updates
- Push changes to your GitHub repository
- Streamlit Community Cloud auto-deploys on git push

## 🔐 Security Considerations

- Don't commit sensitive files
- Use environment variables for API keys
- Consider authentication if handling sensitive documents
- Ensure uploaded files are handled securely

## 💡 Tips

1. **Streamlit Community Cloud is free** and perfect for demos
2. **Test locally first** with `streamlit run app.py`
3. **Use meaningful commit messages** for easier debugging
4. **Monitor logs** in the deployment platform for issues
5. **Consider file size limits** for PDF uploads
