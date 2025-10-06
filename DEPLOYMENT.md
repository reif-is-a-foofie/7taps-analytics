# 🚀 Continuous Deployment Pipeline

## **30-90 Second Turnaround: Cursor → Git Push → Live**

This setup gives you a **GitOps-style rapid prototyping pipeline** with cached builds and zero-downtime deployments.

---

## 🎯 **Core Workflow**

Every time you `git push main`:

1. **Cloud Build detects** the change
2. **Builds only changed layers** (cached for speed)
3. **Deploys automatically** to Cloud Run
4. **Swaps traffic** to new revision (no downtime)

**Total turnaround: 30–90 seconds**

---

## 🛠️ **Setup (One-time)**

### 1. Initialize the pipeline
```bash
./setup-triggers.sh
```

This creates:
- **Production trigger**: `main` branch → production deployment
- **Staging trigger**: `dev` branch → staging deployment
- **Required APIs**: Cloud Build, Cloud Run, Artifact Registry

### 2. Configure secrets
```bash
gcloud secrets create gemini-api-key --data-file=- <<< "your-actual-gemini-api-key"
```

---

## 🔄 **Daily Workflow**

### **For rapid prototyping:**
```bash
# Make changes in Cursor
git add .
git commit -m "enhance safety filtering"
git push origin dev          # → deploys to staging
```

### **For production:**
```bash
git checkout main
git merge dev
git push origin main         # → deploys to production
```

---

## 📊 **Services**

- **Production**: `https://safety-api-[hash]-uc.a.run.app`
- **Staging**: `https://safety-api-staging-[hash]-uc.a.run.app`

---

## ⚡ **Speed Optimizations**

### **Docker Caching**
- **Base image stable**: Each cached layer cuts ~20s off builds
- **Dependencies first**: `requirements.txt` changes rarely, gets cached
- **Code last**: Application code changes frequently, rebuilds only when needed

### **Build Machine**
- **E2_HIGHCPU_8**: 8 vCPUs for maximum build speed
- **100GB disk**: Plenty of space for caching
- **Parallel operations**: Multiple steps run concurrently

### **Cloud Run**
- **Traffic swapping**: Zero-downtime deployments
- **Health checks**: Automatic rollback on failure
- **Resource optimization**: Right-sized for your workload

---

## 🔧 **Configuration Files**

- `cloudbuild.yaml` - Production deployment
- `cloudbuild-staging.yaml` - Staging deployment  
- `Dockerfile` - Optimized container with caching
- `.dockerignore` - Excludes unnecessary files

---

## 🎭 **Staging vs Production**

| Feature | Staging | Production |
|---------|---------|------------|
| **Branch** | `dev` | `main` |
| **Memory** | 512Mi | 1Gi |
| **Max Instances** | 5 | 10 |
| **Purpose** | Testing | Live traffic |

---

## 🚨 **Troubleshooting**

### **Build fails?**
```bash
gcloud builds list --limit=5
gcloud builds log [BUILD_ID]
```

### **Deployment fails?**
```bash
gcloud run services list
gcloud run services describe safety-api --region=us-central1
```

### **Trigger not working?**
```bash
gcloud builds triggers list
gcloud builds triggers describe [TRIGGER_ID]
```

---

## 🎯 **Best Practices**

1. **Keep commits small** - Faster builds and easier debugging
2. **Test on staging first** - Use `dev` branch for experimentation
3. **Monitor builds** - Check Cloud Build console for issues
4. **Use descriptive commits** - Makes rollbacks easier
5. **Tag releases** - Use git tags for important deployments

---

## 🔗 **Quick Commands**

```bash
# Check deployment status
gcloud run services list

# View build history
gcloud builds list --limit=10

# Manual deployment (if needed)
gcloud builds submit --config cloudbuild.yaml

# View logs
gcloud run services logs safety-api --region=us-central1
```

---

**This setup gives you enterprise-grade CI/CD with the speed of local development.**
