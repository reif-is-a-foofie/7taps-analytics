# 7taps Analytics - Enhanced Safety Management

Instead of basic CRUD, this system provides **intelligent safety management** that integrates with your existing Gemini AI setup to deliver:

- **Smart word filtering** with AI-powered suggestions
- **Real-time content analysis** combining rule-based and AI detection
- **Pattern recognition** to stay ahead of emerging threats
- **Usage analytics** to optimize your filter effectiveness

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Gemini Integration
Update your Gemini API key in `app/safety_api.py`:
```python
# Replace with your actual Gemini API key
gemini = GeminiSafetyIntegration(api_key="your-actual-gemini-api-key")
```

### 3. Run the API
```bash
cd app
python main.py
```

### 4. Access the UI
Open `http://localhost:8000/static/safety-words.html`

## 🧠 Key Features

### Intelligent Word Management
- **CRUD operations** for filtered words with categories and severity levels
- **Bulk operations** for managing multiple words at once
- **Smart suggestions** from Gemini AI based on content patterns
- **Usage analytics** to track filter effectiveness

### Enhanced Content Analysis
- **Dual-layer detection**: Rule-based filters + Gemini AI analysis
- **Contextual understanding** beyond simple keyword matching
- **Confidence scoring** for more nuanced decision making
- **Pattern recognition** to identify emerging threats

### Advanced Safety Dashboard
- **Real-time filtering controls** with instant feedback
- **Category-based organization** (profanity, harassment, hate speech, etc.)
- **Severity-based prioritization** (1-5 scale)
- **Statistics and analytics** for safety performance

## 📊 API Endpoints

### Word Management
- `GET /api/safety/words` - List filtered words with filtering options
- `POST /api/safety/words` - Create new filtered word
- `PUT /api/safety/words/{id}` - Update existing word
- `DELETE /api/safety/words/{id}` - Remove word from filters
- `POST /api/safety/words/bulk` - Bulk create words

### AI-Powered Features
- `GET /api/safety/suggestions` - Get Gemini AI word suggestions
- `POST /api/safety/suggestions/apply` - Apply selected suggestions
- `POST /api/safety/analyze/enhanced` - Enhanced content analysis
- `GET /api/safety/stats` - Safety statistics and analytics

## 🔧 Integration with Your Existing System

This system is designed to **enhance** your existing safety dashboard at `https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/safety` by:

1. **Extending your Gemini AI** with intelligent word suggestions
2. **Adding CRUD capabilities** for your filtered word list
3. **Providing enhanced analysis** that works alongside your current system
4. **Maintaining compatibility** with your existing safety configuration

## 🎯 Usage Examples

### Add a New Filtered Word
```python
import requests

response = requests.post("http://localhost:8000/api/safety/words", json={
    "word": "inappropriate_content",
    "category": "inappropriate",
    "severity": 3,
    "is_active": True
})
```

### Get AI Suggestions
```python
suggestions = requests.get("http://localhost:8000/api/safety/suggestions")
# Returns Gemini-powered suggestions based on your content patterns
```

### Enhanced Content Analysis
```python
analysis = requests.post("http://localhost:8000/api/safety/analyze/enhanced", 
                        json={"content": "Content to analyze"})
# Returns both rule-based matches and Gemini AI insights
```

## 🔒 Security Considerations

- **API keys**: Store your Gemini API key securely (use environment variables)
- **Rate limiting**: Implement rate limiting for production use
- **Input validation**: All inputs are validated and sanitized
- **CORS**: Configure CORS properly for your domain in production

## 🚀 Production Deployment

1. **Database**: Replace in-memory storage with PostgreSQL
2. **Authentication**: Add proper authentication/authorization
3. **Rate limiting**: Implement rate limiting middleware
4. **Monitoring**: Add logging and monitoring
5. **Scaling**: Use async processing for high-volume analysis

## 📈 Next Steps

1. **Integrate with your existing Gemini setup** by updating the API key
2. **Deploy alongside your current system** for enhanced capabilities
3. **Monitor effectiveness** using the built-in analytics
4. **Expand with custom categories** based on your specific needs

This system transforms basic CRUD into **intelligent safety management** that grows smarter with your content patterns.
