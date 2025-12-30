# 🚀 AGENDA

**Agent for Goal Execution, Navigation & Day Allocation**

AGENDA is an intelligent productivity and goal management application built with Streamlit. It combines AI-powered assistance with integrations for Google Calendar, Gmail, GitHub, and web search to help you stay organized and productive.

![AGENDA](assets/agenda.png)

---

## ✨ Features

### 📊 Dashboard
- Overview of your tasks, calendar events, and productivity metrics
- AI-powered insights and recommendations

### 📅 Calendar Integration
- Connect your Google Calendar
- View and manage events seamlessly
- AI-assisted scheduling

### 📧 Gmail Integration
- Read and send emails directly from the app
- AI-powered email composition and management

### 🐙 GitHub Integration
- Connect your GitHub repositories
- Track issues and pull requests
- Collaborate with team members

### 🔍 Web Search
- DuckDuckGo integration for web, image, and news searches
- Research without leaving the app

### 🗓️ Today's Plan
- AI-generated daily planning
- Prioritized task lists
- Smart time allocation

### ✅ Workboard (Todo)
- Manage tasks and projects
- Track progress and deadlines

### 👥 Collaborators
- Team collaboration features
- Share and coordinate with others

---

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **AI/LLM**: OpenAI GPT, LangChain, LangGraph
- **Database**: PostgreSQL
- **APIs**: Google Calendar, Gmail, GitHub, DuckDuckGo

---

## 📋 Prerequisites

- **Python 3.11+**
- **PostgreSQL** database
- **uv** package manager ([Install uv](https://github.com/astral-sh/uv))
- API keys/credentials for:
  - OpenAI API
  - Google OAuth (for Calendar & Gmail)
  - GitHub OAuth (optional)

---

## 🚀 Quick Start with UV

### 1. Clone the Repository

```bash
git clone https://github.com/ctrlxharsh/agenda.git
cd agenda
```

### 2. Create Virtual Environment with UV

```bash
# Install uv if you haven't already
pip install uv

# Create a virtual environment
uv venv

# Activate the virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
.venv\Scripts\activate.bat

# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install all dependencies using uv
uv pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# PostgreSQL Database
DATABASE_URL=postgresql://user:password@localhost:5432/agenda
# Or use individual variables:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agenda
DB_USER=your_username
DB_PASSWORD=your_password

# Google OAuth (for Calendar & Gmail)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# GitHub OAuth (optional)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### 5. Initialize the Database

```bash
# Run the schema.sql to set up database tables
psql -U your_username -d agenda -f schema.sql
```

### 6. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📁 Project Structure

```
agenda/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── schema.sql            # Database schema
├── .env                  # Environment variables (create this)
├── assets/               # Static assets (images, etc.)
│   └── agenda.png
├── styles/               # Custom CSS styles
│   └── main.css
├── pages/                # Application pages
│   ├── login/           # Authentication
│   ├── home/            # Dashboard
│   ├── calendar/        # Calendar management
│   ├── profile/         # User profile
│   ├── todays_plan/     # Daily planning
│   ├── todo/            # Task management (Workboard)
│   ├── collaborators/   # Team collaboration
│   └── authorization/   # OAuth & API connections
├── mcp_models/          # MCP (Model Context Protocol) integrations
│   ├── calendar.py      # Google Calendar integration
│   ├── gmail.py         # Gmail integration
│   ├── github.py        # GitHub integration
│   ├── search.py        # DuckDuckGo search
│   └── linkedin.py      # LinkedIn integration
└── utils/               # Utility functions
    └── github_auth.py   # GitHub authentication helpers
```

---

## 🔧 Development

### Running in Development Mode

```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Run with auto-reload
streamlit run app.py --server.runOnSave true
```

### Adding New Dependencies

```bash
# Add a new package
uv pip install package_name

# Update requirements.txt
uv pip freeze > requirements.txt
```

---

## 🔐 Setting Up OAuth

### Google OAuth (Calendar & Gmail)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API** and **Gmail API**
4. Create OAuth 2.0 credentials
5. Download `client_secret.json` and place it in the root directory
6. Add `http://localhost:8501` to authorized redirect URIs

### GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set Homepage URL to `http://localhost:8501`
4. Set Authorization callback URL to `http://localhost:8501`
5. Copy Client ID and Client Secret to your `.env` file

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📧 Contact

**Harsh** - [@ctrlxharsh](https://github.com/ctrlxharsh)

Project Link: [https://github.com/ctrlxharsh/agenda](https://github.com/ctrlxharsh/agenda)

---

<div align="center">
  <p>Made with ❤️ and ☕</p>
  <p>🚀 <strong>AGENDA</strong> - Your AI-Powered Productivity Companion</p>
</div>