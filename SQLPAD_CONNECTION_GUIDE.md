# 🗄️ SQLPad Heroku Database Connection Guide

## ✅ **SQLPad Status**
- **URL**: http://localhost:3000
- **Login**: admin@7taps.com / admin123
- **Status**: ✅ Running and accessible
- **Auto-Configuration**: ✅ **AUTOMATICALLY CONFIGURED!**

## 🚀 **Automatic Configuration**

The system now automatically configures SQLPad with the Heroku database connection! 

**To run the auto-configuration:**
```bash
python3 scripts/auto_configure_sqlpad.py
```

**To verify the connection:**
```bash
python3 scripts/verify_sqlpad_data.py
```

## 🔧 **Manual Connection Setup (Fallback)**

If automatic configuration fails, you can manually configure the connection in SQLPad.

### **Step 1: Access SQLPad**
1. Go to: http://localhost:3000
2. Login with: `admin@7taps.com` / `admin123`

### **Step 2: Add Database Connection**
1. Click **"Connections"** in the left sidebar
2. Click **"New Connection"** button
3. Fill in the connection details:

**Connection Settings:**
- **Name**: `7taps Analytics Database`
- **Driver**: `PostgreSQL`
- **Host**: `c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com`
- **Port**: `5432`
- **Database**: `d7s5ke2hmuqipn`
- **Username**: `u19o5qm786p1d1`
- **Password**: `p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2`

**Advanced Settings:**
- **SSL**: ✅ Check "Use SSL"
- **SSL Mode**: `require` (NOT `verify-full` or `verify-ca`)
- **SSL Certificate Verification**: Disable if available

### **Alternative: Connection String Method**
If the above doesn't work, try using a connection string:

**Connection String:**
```
postgresql://u19o5qm786p1d1:p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2@c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7s5ke2hmuqipn?sslmode=require
```

### **Step 3: Test Connection**
1. Click **"Test Connection"** button
2. If successful, click **"Save"**
3. You should see the connection in your connections list

### **Step 4: Start Querying**
1. Click **"New Query"** button
2. Select your **"7taps Analytics Database"** connection
3. Start with a simple test query:

```sql
-- Test connection
SELECT COUNT(*) as total_users FROM users;

-- Check available tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

## 📊 **Sample Queries to Try**

### **Basic Analytics**
```sql
-- Total users and activity
SELECT 
    COUNT(DISTINCT u.id) as total_users,
    COUNT(ua.id) as total_activities,
    COUNT(ur.id) as total_responses
FROM users u
LEFT JOIN user_activities ua ON u.id = ua.user_id
LEFT JOIN user_responses ur ON u.id = ur.user_id;
```

### **Lesson Completion**
```sql
-- Lesson completion rates
SELECT 
    l.lesson_name,
    COUNT(DISTINCT ua.user_id) as users_started,
    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed
FROM lessons l
LEFT JOIN user_activities ua ON l.id = ua.lesson_id
GROUP BY l.id, l.lesson_name
ORDER BY l.lesson_number;
```

### **Recent Activity**
```sql
-- Recent user activity
SELECT 
    u.user_id,
    ua.activity_type,
    l.lesson_name,
    ua.timestamp
FROM user_activities ua
JOIN users u ON ua.user_id = u.id
LEFT JOIN lessons l ON ua.lesson_id = l.id
ORDER BY ua.timestamp DESC
LIMIT 20;
```

## 🔍 **Troubleshooting**

### **SSL Connection Issues**
If you get SSL-related errors like "unable to get local issuer certificate":
1. Make sure **"Use SSL"** is checked
2. Use SSL mode: `require` (NOT `verify-full` or `verify-ca`)
3. If available, disable SSL certificate verification
4. Check that the host and credentials are correct

### **Connection Refused**
If connection is refused:
1. Verify the host: `c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com`
2. Check the port: `5432`
3. Ensure the database name: `d7s5ke2hmuqipn`

### **Authentication Failed**
If authentication fails:
1. Double-check username: `u19o5qm786p1d1`
2. Verify password: `p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2`
3. Make sure there are no extra spaces

## 🎯 **Expected Results**

Once connected, you should see:
- **16 tables** including users, lessons, user_activities, user_responses, etc.
- **Real data** from your production Heroku database
- **All sample queries** returning actual results

## 🚀 **Quick Access**

- **Dashboard**: http://localhost:8000 (with Database Terminal link)
- **SQLPad Direct**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

---

*This manual setup ensures proper SSL encryption required by Heroku PostgreSQL.*
