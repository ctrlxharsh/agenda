

from typing import Any, Dict, List, Optional
import requests, base64, asyncio
from pages.authorization.data import get_github_access_token, check_github_connection

GITHUB_API_BASE = "https://api.github.com"


class MCPGitHubTools:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self._access_token = None
    
    def _get_token(self) -> Optional[str]:
        """Get cached or fetch access token."""
        if not self._access_token:
            self._access_token = get_github_access_token(self.user_id)
        return self._access_token
    
    def _headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def is_connected(self) -> Dict[str, Any]:
        status = await asyncio.to_thread(check_github_connection, self.user_id)
        if status:
            return {
                'success': True,
                'connected': True,
                'username': status['username'],
                'message': f"GitHub connected as @{status['username']}"
            }
        return {
            'success': True,
            'connected': False,
            'message': "GitHub not connected. Please connect your GitHub account in the Authorization page."
        }
    
    # ========== REPOSITORY INTELLIGENCE (READ) ==========
    
    async def list_repositories(
        self,
        visibility: str = "all",
        sort: str = "updated",
        limit: int = 30
    ) -> Dict[str, Any]:
        """List user's repositories."""
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            def _fetch_repos():
                return requests.get(
                    f"{GITHUB_API_BASE}/user/repos",
                    headers=self._headers(),
                    params={
                        "visibility": visibility,
                        "sort": sort,
                        "per_page": min(limit, 100)
                    }
                )
            
            response = await asyncio.to_thread(_fetch_repos)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            repos = response.json()
            repo_list = [
                {
                    'name': repo['name'],
                    'full_name': repo['full_name'],
                    'description': repo['description'] or '',
                    'private': repo['private'],
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'language': repo['language'],
                    'url': repo['html_url'],
                    'updated_at': repo['updated_at']
                }
                for repo in repos
            ]
            
            return {
                'success': True,
                'repositories': repo_list,
                'count': len(repo_list),
                'message': f"Found {len(repo_list)} repositories"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_repository_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get detailed repository information."""
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            def _fetch_details():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
                    headers=self._headers()
                )
            
            response = await asyncio.to_thread(_fetch_details)
            
            if response.status_code == 404:
                return {'success': False, 'error': 'Repository not found'}
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            data = response.json()
            
            return {
                'success': True,
                'repository': {
                    'name': data['name'],
                    'full_name': data['full_name'],
                    'description': data['description'] or '',
                    'private': data['private'],
                    'stars': data['stargazers_count'],
                    'forks': data['forks_count'],
                    'watchers': data['watchers_count'],
                    'language': data['language'],
                    'default_branch': data['default_branch'],
                    'topics': data.get('topics', []),
                    'created_at': data['created_at'],
                    'updated_at': data['updated_at'],
                    'url': data['html_url'],
                    'clone_url': data['clone_url'],
                    'open_issues': data['open_issues_count'],
                    'license': data.get('license', {}).get('name') if data.get('license') else None
                },
                'message': f"Repository details for {owner}/{repo}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_repo_structure(
        self,
        owner: str,
        repo: str,
        path: str = ""
    ) -> Dict[str, Any]:
        """List files and folders in a repository path."""
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
            
            def _fetch_structure():
                return requests.get(url, headers=self._headers())
            
            response = await asyncio.to_thread(_fetch_structure)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            contents = response.json()
            
            if isinstance(contents, dict):
                # Single file
                return {
                    'success': True,
                    'type': 'file',
                    'path': path,
                    'items': [{'name': contents['name'], 'type': 'file', 'size': contents.get('size', 0)}]
                }
            
            items = [
                {
                    'name': item['name'],
                    'type': item['type'],  # 'file' or 'dir'
                    'path': item['path'],
                    'size': item.get('size', 0)
                }
                for item in contents
            ]
            
            # Sort: directories first, then files
            items.sort(key=lambda x: (0 if x['type'] == 'dir' else 1, x['name']))
            
            return {
                'success': True,
                'type': 'directory',
                'path': path or '/',
                'items': items,
                'count': len(items),
                'message': f"Found {len(items)} items in {owner}/{repo}/{path or '/'}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def read_file(self, owner: str, repo: str, path: str) -> Dict[str, Any]:
        """Read file content from repository."""
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            def _fetch_file():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}",
                    headers=self._headers()
                )
            
            response = await asyncio.to_thread(_fetch_file)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            data = response.json()
            
            if data.get('type') != 'file':
                return {'success': False, 'error': 'Path is not a file'}
            
            # Decode base64 content
            content = base64.b64decode(data['content']).decode('utf-8')
            
            return {
                'success': True,
                'path': path,
                'content': content,
                'size': data['size'],
                'sha': data['sha'],
                'message': f"Read file: {path}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def summarize_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository summary including README and stats."""
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            # Get repo details first
            details = await self.get_repository_details(owner, repo)
            if not details['success']:
                return details
            
            # Try to get README
            readme_content = ""
            try:
                def _fetch_readme():
                    return requests.get(
                        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme",
                        headers=self._headers()
                    )
                
                readme_response = await asyncio.to_thread(_fetch_readme)
                
                if readme_response.status_code == 200:
                    readme_data = readme_response.json()
                    readme_content = base64.b64decode(readme_data['content']).decode('utf-8')
                    # Truncate if too long
                    if len(readme_content) > 2000:
                        readme_content = readme_content[:2000] + "\n\n... (truncated)"
            except:
                pass
            
            repo_info = details['repository']
            
            return {
                'success': True,
                'summary': {
                    'name': repo_info['name'],
                    'description': repo_info['description'],
                    'language': repo_info['language'],
                    'stars': repo_info['stars'],
                    'forks': repo_info['forks'],
                    'open_issues': repo_info['open_issues'],
                    'topics': repo_info['topics'],
                    'readme': readme_content,
                    'url': repo_info['url']
                },
                'message': f"Summary for {owner}/{repo}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== PROJECT BOOTSTRAPPER (WRITE) ==========
    
    async def create_repository_with_html(
        self,
        name: str,
        description: str = "Created by AI Agent 🚀",
        private: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new repository with a basic HTML website starter.
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether to make it private
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            # Step 1: Create the repository
            def _create_repo():
                return requests.post(
                    f"{GITHUB_API_BASE}/user/repos",
                    headers=self._headers(),
                    json={
                        "name": name,
                        "description": description,
                        "private": private,
                        "auto_init": True  # Creates with README
                    }
                )
            
            create_response = await asyncio.to_thread(_create_repo)
            
            if create_response.status_code == 422:
                return {'success': False, 'error': 'Repository already exists or invalid name'}
            if create_response.status_code != 201:
                return {'success': False, 'error': f"Failed to create repo: {create_response.status_code}"}
            
            repo_data = create_response.json()
            owner = repo_data['owner']['login']
            
            # HTML starter content
            index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="container">
    <h1>Hello from AI Agent 🚀</h1>
    <p>This repository was created automatically.</p>
    <p>Project: <strong>{name}</strong></p>
  </div>
</body>
</html>"""

            style_css = """/* Modern CSS Reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.container {
  background: white;
  padding: 3rem;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
  max-width: 500px;
}

h1 {
  color: #333;
  margin-bottom: 1rem;
  font-size: 2rem;
}

p {
  color: #666;
  margin-bottom: 0.5rem;
  font-size: 1.1rem;
}

strong {
  color: #667eea;
}"""

            readme_md = f"""# {name}

{description}

## 🚀 Quick Start

Open `index.html` in your browser to see the website.

## 📁 Project Structure

```
{name}/
├── index.html    # Main HTML file
├── style.css     # Stylesheet
└── README.md     # This file
```

## 🤖 Created by

This project was automatically generated by an AI Agent.
"""

            # Step 2: Wait for repo to be ready (auto_init takes a moment)
            await asyncio.sleep(2)
            
            # Step 3: Add files
            files_to_create = [
                ("index.html", index_html),
                ("style.css", style_css),
            ]
            
            created_files = []
            file_errors = []
            for filename, content in files_to_create:
                def _put_file(fname=filename, c=content):
                    return requests.put(
                        f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/{fname}",
                        headers=self._headers(),
                        json={
                            "message": f"Add {fname}",
                            "content": base64.b64encode(c.encode()).decode()
                        }
                    )

                file_response = await asyncio.to_thread(_put_file)
                
                if file_response.status_code in [200, 201]:
                    created_files.append(filename)
                else:
                    # Try again if first attempt failed
                    await asyncio.sleep(2)
                    file_response = await asyncio.to_thread(_put_file)
                    
                    if file_response.status_code in [200, 201]:
                        created_files.append(filename)
                    else:
                        file_errors.append(f"{filename}: {file_response.status_code} - {file_response.text[:200]}")
            
            # Step 4: Update README
            def _get_readme():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/README.md",
                    headers=self._headers()
                )
            
            readme_response = await asyncio.to_thread(_get_readme)
            
            if readme_response.status_code == 200:
                readme_sha = readme_response.json()['sha']
                
                def _update_readme():
                    requests.put(
                        f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/README.md",
                        headers=self._headers(),
                        json={
                            "message": "Update README",
                            "content": base64.b64encode(readme_md.encode()).decode(),
                            "sha": readme_sha
                        }
                    )
                
                await asyncio.to_thread(_update_readme)
                created_files.append("README.md")
            
            # Step 5: Enable GitHub Pages (source: root of main branch)
            pages_url = None
            try:
                def _enable_pages():
                    return requests.post(
                        f"{GITHUB_API_BASE}/repos/{owner}/{name}/pages",
                        headers=self._headers(),
                        json={
                            "source": {
                                "branch": "main",
                                "path": "/"
                            }
                        }
                    )
                
                pages_response = await asyncio.to_thread(_enable_pages)
                
                if pages_response.status_code in [201, 200]:
                    pages_data = pages_response.json()
                    pages_url = pages_data.get('html_url', f"https://{owner}.github.io/{name}/")
                else:
                    # Pages might already be enabled or not available
                    pages_url = f"https://{owner}.github.io/{name}/"
            except:
                pages_url = f"https://{owner}.github.io/{name}/"
            
            message = f"✅ Created repository '{name}' with HTML starter!"
            message += f"\n🔗 Repo: {repo_data['html_url']}"
            if pages_url:
                message += f"\n🌐 Pages: {pages_url} (may take a minute to deploy)"
            if file_errors:
                message += f"\n⚠️ Some files failed: {file_errors}"
            
            return {
                'success': True,
                'repository': {
                    'name': name,
                    'full_name': repo_data['full_name'],
                    'url': repo_data['html_url'],
                    'clone_url': repo_data['clone_url'],
                    'private': private,
                    'pages_url': pages_url
                },
                'files_created': created_files,
                'file_errors': file_errors,
                'message': message
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_repository_with_code(
        self,
        name: str = None,
        html_content: str = None,
        css_content: str = "",
        js_content: str = "",
        description: str = "Created by AI Agent 🚀",
        private: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new repository with CUSTOM code provided by the AI.
        Use this when user asks for a specific type of project (game, app, etc).
        
        Args:
            name: Repository name
            html_content: The full HTML code for index.html
            css_content: The CSS code for style.css (optional)
            js_content: The JavaScript code for script.js (optional)
            description: Repository description
            private: Whether to make it private
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
            
        if not name:
            return {'success': False, 'error': 'Repository name is required'}
            
        # Handle missing content
        if not html_content:
            html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>""" + name + """</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f0f0; }
        .container { text-align: center; padding: 2rem; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>""" + name + """</h1>
        <p>Project created by AI Agent.</p>
        <p><em>No code was provided, so this is a placeholder.</em></p>
    </div>
</body>
</html>"""
        
        try:
            # Step 1: Create the repository
            def _create_repo():
                return requests.post(
                    f"{GITHUB_API_BASE}/user/repos",
                    headers=self._headers(),
                    json={
                        "name": name,
                        "description": description,
                        "private": private,
                        "auto_init": True
                    }
                )
            
            create_response = await asyncio.to_thread(_create_repo)
            
            if create_response.status_code == 422:
                return {'success': False, 'error': 'Repository already exists or invalid name'}
            if create_response.status_code != 201:
                return {'success': False, 'error': f"Failed to create repo: {create_response.status_code}"}
            
            repo_data = create_response.json()
            owner = repo_data['owner']['login']
            
            # Wait for repo to be ready
            await asyncio.sleep(2)
            
            # Step 2: Add files
            files_to_create = [("index.html", html_content)]
            if css_content:
                files_to_create.append(("style.css", css_content))
            if js_content:
                files_to_create.append(("script.js", js_content))
            
            created_files = []
            file_errors = []
            
            for filename, content in files_to_create:
                def _put_file(fname=filename, c=content):
                    return requests.put(
                        f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/{fname}",
                        headers=self._headers(),
                        json={
                            "message": f"Add {fname}",
                            "content": base64.b64encode(c.encode()).decode()
                        }
                    )
                
                file_response = await asyncio.to_thread(_put_file)
                
                if file_response.status_code in [200, 201]:
                    created_files.append(filename)
                else:
                    await asyncio.sleep(2)
                    file_response = await asyncio.to_thread(_put_file)
                    
                    if file_response.status_code in [200, 201]:
                        created_files.append(filename)
                    else:
                        file_errors.append(f"{filename}: {file_response.status_code}")
            
            # Step 3: Create README
            readme_md = f"""# {name}

{description}

## 🚀 Live Demo

Open `index.html` in your browser or visit the GitHub Pages URL.

## 🤖 Created by AI Agent
"""
            def _get_readme():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/README.md",
                    headers=self._headers()
                )
            
            readme_response = await asyncio.to_thread(_get_readme)
            
            if readme_response.status_code == 200:
                readme_sha = readme_response.json()['sha']
                
                def _update_readme():
                    requests.put(
                        f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/README.md",
                        headers=self._headers(),
                        json={
                            "message": "Update README",
                            "content": base64.b64encode(readme_md.encode()).decode(),
                            "sha": readme_sha
                        }
                    )
                
                await asyncio.to_thread(_update_readme)
                created_files.append("README.md")
            
            # Step 4: Enable GitHub Pages
            pages_url = None
            try:
                def _enable_pages():
                    return requests.post(
                        f"{GITHUB_API_BASE}/repos/{owner}/{name}/pages",
                        headers=self._headers(),
                        json={"source": {"branch": "main", "path": "/"}}
                    )
                
                pages_response = await asyncio.to_thread(_enable_pages)
                
                if pages_response.status_code in [201, 200]:
                    pages_url = f"https://{owner}.github.io/{name}/"
                else:
                    pages_url = f"https://{owner}.github.io/{name}/"
            except:
                pages_url = f"https://{owner}.github.io/{name}/"
            
            message = f"✅ Created '{name}' with your custom code!"
            message += f"\n🔗 Repo: {repo_data['html_url']}"
            message += f"\n🌐 Pages: {pages_url}"
            
            return {
                'success': True,
                'repository': {
                    'name': name,
                    'url': repo_data['html_url'],
                    'pages_url': pages_url
                },
                'files_created': created_files,
                'message': message
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    

    async def create_empty_repository(
        self,
        name: str,
        project_type: str = "python",
        description: str = "Created by AI Agent 🚀",
        private: bool = False,
        license_type: str = "mit"
    ) -> Dict[str, Any]:
        
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        # Gitignore templates
        gitignore_templates = {
            "python": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/
.eggs/
*.egg
.mypy_cache/
.pytest_cache/
.coverage
htmlcov/
.env
*.log""",
            "node": """# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.env
.env.local
.env.*.local
dist/
build/
*.log""",
            "java": """# Java
*.class
*.jar
*.war
*.ear
target/
.gradle/
build/
.idea/
*.iml
.classpath
.project
.settings/""",
            "go": """# Go
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test
*.out
go.work
vendor/""",
            "rust": """# Rust
/target/
Cargo.lock
*.rs.bk""",
            "general": """# General
.DS_Store
Thumbs.db
*.log
*.tmp
.env
.idea/
.vscode/
*.swp
*~"""
        }
        
        try:
            # Step 1: Create the repository with auto_init for README
            def _create_repo():
                return requests.post(
                    f"{GITHUB_API_BASE}/user/repos",
                    headers=self._headers(),
                    json={
                        "name": name,
                        "description": description,
                        "private": private,
                        "auto_init": True,
                        "license_template": license_type
                    }
                )
            
            create_response = await asyncio.to_thread(_create_repo)
            
            if create_response.status_code == 422:
                return {'success': False, 'error': 'Repository already exists or invalid name'}
            if create_response.status_code != 201:
                return {'success': False, 'error': f"Failed to create repo: {create_response.status_code}"}
            
            repo_data = create_response.json()
            owner = repo_data['owner']['login']
            
            # Wait for repo to be ready
            await asyncio.sleep(2)
            
            # Step 2: Add .gitignore
            gitignore_content = gitignore_templates.get(project_type.lower(), gitignore_templates["general"])
            
            def _put_gitignore():
                return requests.put(
                    f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/.gitignore",
                    headers=self._headers(),
                    json={
                        "message": f"Add .gitignore for {project_type}",
                        "content": base64.b64encode(gitignore_content.encode()).decode()
                    }
                )
            
            await asyncio.to_thread(_put_gitignore)
            
            # Step 3: Update README with better content
            readme_md = f"""# {name}

{description}

## Getting Started

```bash
git clone {repo_data['clone_url']}
cd {name}
```

## Project Type
{project_type.capitalize()}

## License
{license_type.upper()}

---
*Created by AI Agent 🚀*
"""
            def _get_readme():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/README.md",
                    headers=self._headers()
                )
            
            readme_response = await asyncio.to_thread(_get_readme)
            
            if readme_response.status_code == 200:
                readme_sha = readme_response.json()['sha']
                
                def _update_readme():
                    requests.put(
                        f"{GITHUB_API_BASE}/repos/{owner}/{name}/contents/README.md",
                        headers=self._headers(),
                        json={
                            "message": "Update README",
                            "content": base64.b64encode(readme_md.encode()).decode(),
                            "sha": readme_sha
                        }
                    )
                
                await asyncio.to_thread(_update_readme)
            
            clone_cmd = f"git clone {repo_data['clone_url']}"
            
            message = f"✅ Created '{name}' repository!"
            message += f"\n📋 Type: {project_type}"
            message += f"\n📜 License: {license_type.upper()}"
            message += f"\n🔗 URL: {repo_data['html_url']}"
            message += f"\n\n**Clone:**\n```\n{clone_cmd}\n```"
            
            return {
                'success': True,
                'repository': {
                    'name': name,
                    'full_name': repo_data['full_name'],
                    'url': repo_data['html_url'],
                    'clone_url': repo_data['clone_url'],
                    'ssh_url': repo_data['ssh_url'],
                    'private': private,
                    'project_type': project_type,
                    'license': license_type
                },
                'clone_command': clone_cmd,
                'message': message
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== ISSUES (READ + WRITE) ==========
    
    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        List issues in a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: "open", "closed", or "all"
            limit: Max issues to return
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            def _fetch_issues():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
                    headers=self._headers(),
                    params={"state": state, "per_page": min(limit, 100)}
                )
            
            response = await asyncio.to_thread(_fetch_issues)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            issues = response.json()
            # Filter out pull requests (they come in issues endpoint)
            issues = [i for i in issues if 'pull_request' not in i]
            
            issue_list = [
                {
                    'number': issue['number'],
                    'title': issue['title'],
                    'state': issue['state'],
                    'labels': [l['name'] for l in issue['labels']],
                    'author': issue['user']['login'],
                    'created_at': issue['created_at'],
                    'comments': issue['comments'],
                    'url': issue['html_url']
                }
                for issue in issues
            ]
            
            return {
                'success': True,
                'issues': issue_list,
                'count': len(issue_list),
                'message': f"Found {len(issue_list)} {state} issues in {owner}/{repo}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body (markdown)
            labels: List of label names
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            payload = {"title": title, "body": body}
            if labels:
                payload["labels"] = labels
            
            def _post_issue():
                return requests.post(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
                    headers=self._headers(),
                    json=payload
                )
            
            response = await asyncio.to_thread(_post_issue)
            
            if response.status_code != 201:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            issue = response.json()
            
            return {
                'success': True,
                'issue': {
                    'number': issue['number'],
                    'title': issue['title'],
                    'url': issue['html_url']
                },
                'message': f"✅ Created issue #{issue['number']}: {title}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: str = None,
        body: str = None,
        state: str = None,
        labels: List[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            title: New title (optional)
            body: New body (optional)
            state: "open" or "closed" (optional)
            labels: New labels (optional)
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            payload = {}
            if title: payload["title"] = title
            if body: payload["body"] = body
            if state: payload["state"] = state
            if labels is not None: payload["labels"] = labels
            
            def _patch_issue():
                return requests.patch(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}",
                    headers=self._headers(),
                    json=payload
                )
            
            response = await asyncio.to_thread(_patch_issue)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            issue = response.json()
            
            return {
                'success': True,
                'issue': {
                    'number': issue['number'],
                    'title': issue['title'],
                    'state': issue['state'],
                    'url': issue['html_url']
                },
                'message': f"✅ Updated issue #{issue_number}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def close_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Close an issue."""
        return await self.update_issue(owner, repo, issue_number, state="closed")
    
    # ========== PULL REQUESTS (READ + WRITE) ==========
    
    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        List pull requests in a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: "open", "closed", or "all"
            limit: Max PRs to return
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            def _fetch_prs():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
                    headers=self._headers(),
                    params={"state": state, "per_page": min(limit, 100)}
                )
            
            response = await asyncio.to_thread(_fetch_prs)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            prs = response.json()
            pr_list = [
                {
                    'number': pr['number'],
                    'title': pr['title'],
                    'state': pr['state'],
                    'author': pr['user']['login'],
                    'base': pr['base']['ref'],
                    'head': pr['head']['ref'],
                    'created_at': pr['created_at'],
                    'url': pr['html_url'],
                    'draft': pr.get('draft', False)
                }
                for pr in prs
            ]
            
            return {
                'success': True,
                'pull_requests': pr_list,
                'count': len(pr_list),
                'message': f"Found {len(pr_list)} {state} pull requests in {owner}/{repo}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def summarize_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """
        Get PR details including diff summary.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            # Get PR details
            def _fetch_pr():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers=self._headers()
                )
            
            pr_response = await asyncio.to_thread(_fetch_pr)
            
            if pr_response.status_code != 200:
                return {'success': False, 'error': f"PR not found: {pr_response.status_code}"}
            
            pr = pr_response.json()
            
            # Get files changed
            def _fetch_files():
                return requests.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                    headers=self._headers()
                )
            
            files_response = await asyncio.to_thread(_fetch_files)
            
            files = []
            if files_response.status_code == 200:
                files = [
                    {
                        'filename': f['filename'],
                        'status': f['status'],
                        'additions': f['additions'],
                        'deletions': f['deletions']
                    }
                    for f in files_response.json()[:20]  # Limit to 20 files
                ]
            
            return {
                'success': True,
                'pull_request': {
                    'number': pr['number'],
                    'title': pr['title'],
                    'body': pr['body'] or '',
                    'state': pr['state'],
                    'author': pr['user']['login'],
                    'base': pr['base']['ref'],
                    'head': pr['head']['ref'],
                    'mergeable': pr.get('mergeable'),
                    'commits': pr['commits'],
                    'additions': pr['additions'],
                    'deletions': pr['deletions'],
                    'changed_files': pr['changed_files'],
                    'url': pr['html_url']
                },
                'files_changed': files,
                'message': f"PR #{pr_number}: {pr['title']}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def comment_on_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str
    ) -> Dict[str, Any]:
        """
        Add a comment to a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            body: Comment body (markdown)
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            # PR comments use issues endpoint
            def _post_comment():
                return requests.post(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                    headers=self._headers(),
                    json={"body": body}
                )
            
            response = await asyncio.to_thread(_post_comment)
            
            if response.status_code != 201:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            comment = response.json()
            
            return {
                'success': True,
                'comment': {
                    'id': comment['id'],
                    'url': comment['html_url']
                },
                'message': f"✅ Added comment to PR #{pr_number}"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== NOTIFICATIONS (READ + WRITE) ==========
    
    async def read_notifications(self, all_notifications: bool = False) -> Dict[str, Any]:
        """
        Get user's GitHub notifications.
        
        Args:
            all_notifications: If True, get all (including read). Otherwise only unread.
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            def _fetch_notifications():
                return requests.get(
                    f"{GITHUB_API_BASE}/notifications",
                    headers=self._headers(),
                    params={"all": str(all_notifications).lower()}
                )
            
            response = await asyncio.to_thread(_fetch_notifications)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            notifications = response.json()
            notif_list = [
                {
                    'id': n['id'],
                    'reason': n['reason'],
                    'unread': n['unread'],
                    'title': n['subject']['title'],
                    'type': n['subject']['type'],
                    'repo': n['repository']['full_name'],
                    'updated_at': n['updated_at']
                }
                for n in notifications[:50]  # Limit
            ]
            
            return {
                'success': True,
                'notifications': notif_list,
                'count': len(notif_list),
                'message': f"Found {len(notif_list)} notifications"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def mark_notification_as_read(self, notification_id: str) -> Dict[str, Any]:
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
        """
        if not self._get_token():
            return {'success': False, 'error': 'GitHub not connected'}
        
        try:
            def _patch_notification():
                return requests.patch(
                    f"{GITHUB_API_BASE}/notifications/threads/{notification_id}",
                    headers=self._headers()
                )
            
            response = await asyncio.to_thread(_patch_notification)
            
            if response.status_code not in [200, 205]:
                return {'success': False, 'error': f"GitHub API error: {response.status_code}"}
            
            return {
                'success': True,
                'message': f"✅ Marked notification {notification_id} as read"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ========== TOOL DEFINITIONS FOR MCP ==========

def get_github_tools(user_id: int) -> List[Dict[str, Any]]:
    """
    Get available GitHub MCP tools for the given user.
    
    Args:
        user_id: User ID to create tools for
        
    Returns:
        List of tool definitions in MCP format
    """
    # Check connection synchronously
    connection = check_github_connection(user_id)
    
    if not connection or not connection.get('connected'):
        return []  # No tools if not connected
    
    return [
        # Repository Intelligence
        {
            "name": "github_list_repositories",
            "description": "List the user's GitHub repositories. Returns repo names, descriptions, stars, and languages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "visibility": {"type": "string", "enum": ["all", "public", "private"], "default": "all"},
                    "sort": {"type": "string", "enum": ["created", "updated", "pushed", "full_name"], "default": "updated"},
                    "limit": {"type": "integer", "default": 30}
                }
            }
        },
        {
            "name": "github_get_repository_details",
            "description": "Get detailed information about a specific repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner username"},
                    "repo": {"type": "string", "description": "Repository name"}
                },
                "required": ["owner", "repo"]
            }
        },
        {
            "name": "github_get_repo_structure",
            "description": "List files and folders in a repository path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "path": {"type": "string", "default": "", "description": "Path within repo, empty for root"}
                },
                "required": ["owner", "repo"]
            }
        },
        {
            "name": "github_read_file",
            "description": "Read the contents of a file from a repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "path": {"type": "string", "description": "File path in the repository"}
                },
                "required": ["owner", "repo", "path"]
            }
        },
        {
            "name": "github_summarize_repository",
            "description": "Get a summary of a repository including README and stats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"}
                },
                "required": ["owner", "repo"]
            }
        },
        {
            "name": "github_create_repository_with_code",
            "description": "Create a repository with CUSTOM code. Use this when user asks for a specific project (game, app, etc). You MUST generate the full HTML/CSS/JS code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Repository name"},
                    "html_content": {"type": "string", "description": "Full HTML code for index.html"},
                    "css_content": {"type": "string", "description": "CSS code for style.css"},
                    "js_content": {"type": "string", "description": "JavaScript code for script.js"},
                    "description": {"type": "string", "default": "Created by AI Agent 🚀"},
                    "private": {"type": "boolean", "default": False}
                },
                "required": ["name", "html_content"]
            }
        },
        {
            "name": "github_create_empty_repository",
            "description": "Create an empty repository with README, .gitignore (based on project type), and license. Returns clone command. Use for initializing new coding projects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Repository name"},
                    "project_type": {"type": "string", "enum": ["python", "node", "java", "go", "rust", "general"], "description": "Type for .gitignore", "default": "python"},
                    "description": {"type": "string", "default": "Created by AI Agent 🚀"},
                    "private": {"type": "boolean", "default": False},
                    "license_type": {"type": "string", "enum": ["mit", "apache-2.0", "gpl-3.0", "bsd-3-clause"], "default": "mit"}
                },
                "required": ["name"]
            }
        },
        # Issues
        {
            "name": "github_list_issues",
            "description": "List issues in a repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                    "limit": {"type": "integer", "default": 30}
                },
                "required": ["owner", "repo"]
            }
        },
        {
            "name": "github_create_issue",
            "description": "Create a new issue in a repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string", "default": ""},
                    "labels": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["owner", "repo", "title"]
            }
        },
        {
            "name": "github_close_issue",
            "description": "Close an issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "issue_number": {"type": "integer"}
                },
                "required": ["owner", "repo", "issue_number"]
            }
        },
        # Pull Requests
        {
            "name": "github_list_pull_requests",
            "description": "List pull requests in a repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                    "limit": {"type": "integer", "default": 30}
                },
                "required": ["owner", "repo"]
            }
        },
        {
            "name": "github_summarize_pull_request",
            "description": "Get detailed PR summary including files changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "pr_number": {"type": "integer"}
                },
                "required": ["owner", "repo", "pr_number"]
            }
        },
        {
            "name": "github_comment_on_pull_request",
            "description": "Add a comment to a pull request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "pr_number": {"type": "integer"},
                    "body": {"type": "string"}
                },
                "required": ["owner", "repo", "pr_number", "body"]
            }
        },
        # Notifications
        {
            "name": "github_read_notifications",
            "description": "Get GitHub notifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "all_notifications": {"type": "boolean", "default": False, "description": "Include read notifications"}
                }
            }
        },
        {
            "name": "github_mark_notification_as_read",
            "description": "Mark a notification as read.",
            "parameters": {
                "type": "object",
                "properties": {
                    "notification_id": {"type": "string"}
                },
                "required": ["notification_id"]
            }
        },
        # Connection check
        {
            "name": "github_is_connected",
            "description": "Check if user has GitHub connected and get username.",
            "parameters": {"type": "object", "properties": {}}
        }
    ]


async def execute_github_tool(user_id: int, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a GitHub MCP tool by name.
    
    Args:
        user_id: User ID executing the tool
        tool_name: Name of the tool to execute
        parameters: Parameters to pass to the tool
        
    Returns:
        Tool execution result
    """
    tools = MCPGitHubTools(user_id)
    
    # Map tool names to methods
    tool_map = {
        "github_is_connected": lambda: tools.is_connected(),
        "github_list_repositories": lambda: tools.list_repositories(**parameters),
        "github_get_repository_details": lambda: tools.get_repository_details(**parameters),
        "github_get_repo_structure": lambda: tools.get_repo_structure(**parameters),
        "github_read_file": lambda: tools.read_file(**parameters),
        "github_summarize_repository": lambda: tools.summarize_repository(**parameters),
        "github_create_repository_with_code": lambda: tools.create_repository_with_code(**parameters),
        "github_create_empty_repository": lambda: tools.create_empty_repository(**parameters),
        "github_list_issues": lambda: tools.list_issues(**parameters),
        "github_create_issue": lambda: tools.create_issue(**parameters),
        "github_close_issue": lambda: tools.close_issue(**parameters),
        "github_list_pull_requests": lambda: tools.list_pull_requests(**parameters),
        "github_summarize_pull_request": lambda: tools.summarize_pull_request(**parameters),
        "github_comment_on_pull_request": lambda: tools.comment_on_pull_request(**parameters),
        "github_read_notifications": lambda: tools.read_notifications(**parameters),
        "github_mark_notification_as_read": lambda: tools.mark_notification_as_read(**parameters),
    }
    
    if tool_name not in tool_map:
        return {'success': False, 'error': f"Unknown GitHub tool: {tool_name}"}
    
    try:
        return await tool_map[tool_name]()
    except Exception as e:
        return {'success': False, 'error': f"Tool execution failed: {str(e)}"}
