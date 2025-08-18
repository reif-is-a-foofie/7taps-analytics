# 🧠 Seven Analytics - Streamlit Chat Interface

A beautiful, interactive chat interface for exploring your 7taps learning analytics data with real-time visualizations.

## Features

- **💬 Natural Language Chat**: Talk to "Seven" your AI data analyst
- **📊 Real-time Visualizations**: See charts and graphs update as you ask questions
- **💾 Save & Load**: Store interesting visualizations for later reference
- **🔗 Unified Data**: Access both CSV focus group data and xAPI real-time activities
- **🎨 Beautiful UI**: Clean, modern interface inspired by Streamlit's playground

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the app**:
   ```bash
   python run_streamlit.py
   ```
   
   Or directly with Streamlit:
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Open your browser** to `http://localhost:8501`

## How to Use

### Chat Interface (Left Side)
- Type natural language questions like:
  - "Show me focus group responses by lesson"
  - "What are the engagement trends?"
  - "How many total statements do we have?"
  - "Compare activity between CSV and xAPI sources"

### Visualization Panel (Right Side)
- Charts automatically appear based on your questions
- Click "Save Visualization" to store interesting charts
- Load previously saved visualizations from the history

## Example Questions

**Data Overview:**
- "Show me total statements by source"
- "How many unique learners do we have?"

**Focus Group Analysis:**
- "Focus group responses by lesson"
- "What are the most common responses?"

**Engagement Trends:**
- "Show me recent activity timeline"
- "Daily engagement patterns"

**Cross-Source Analysis:**
- "Compare engagement between CSV and xAPI"
- "Which source has more active learners?"

## Data Schema

The interface connects to your unified analytics database with:

- **`statements_new`**: Core learning statements (633 total)
- **`results_new`**: Learning results and scores
- **`context_extensions_new`**: Extended context data

**Data Sources:**
- 373 CSV focus group responses
- 260 xAPI real-time activities

## Integration with OpenAI

The system is designed to work with ChatGPT/OpenAI for enhanced natural language processing. The `SYSTEM_CONTEXT` in `streamlit_app.py` contains all the preloaded information about your data schema, common queries, and response formatting.

## Customization

### Adding New Visualizations
Edit the `create_visualization()` function to add new chart types.

### Extending Bot Responses
Modify the `generate_bot_response()` function to add more query patterns.

### Styling
Update the CSS in the `st.markdown()` section to customize the appearance.

## Troubleshooting

**App won't start:**
- Check that all dependencies are installed
- Ensure the Heroku backend is running
- Verify database connectivity

**No visualizations appear:**
- Check the browser console for errors
- Verify the API endpoint is accessible
- Test with a simple query first

**Chat not responding:**
- Check the Streamlit logs
- Verify the database query endpoint is working
- Test the API directly with curl

## Next Steps

1. **Integrate OpenAI**: Replace the rule-based responses with ChatGPT
2. **Add More Chart Types**: Pie charts, scatter plots, heatmaps
3. **Export Features**: Download charts as PNG/PDF
4. **Advanced Analytics**: Add statistical analysis and insights
5. **Real-time Updates**: Live data streaming from the database

---

Built with ❤️ for 7taps Analytics
