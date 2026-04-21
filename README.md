[![Version française](https://img.shields.io/badge/Lire%20en-Fran%C3%A7ais-blue?style=for-the-badge&logo=appveyor)](https://github.com/Bishoko/Bishokus/blob/main/README-fr.md)

# 🎭 Bishokus

> **A versatile French Discord bot designed to enhance and entertain your server.** (also available in English)

<div align="center">

  <img src="https://cdn.discordapp.com/avatars/888484118852145182/1720decdb60d00751b44e7c28c1a14b0.webp?size=512" alt="Bishokus Logo" width="35%" height="35%">
  
  <br>

  [![GitHub release (latest by date)](https://img.shields.io/github/v/release/Bishoko/Bishokus.svg?style=flat-square)](https://github.com/Bishoko/Bishokus/releases)
  [![GitHub stars](https://img.shields.io/github/stars/Bishoko/Bishokus.svg?style=flat-square)](https://github.com/Bishoko/Bishokus/stargazers)
  ![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Bishoko/Bishokus/ci.yml?style=flat-square)
  [![GitHub issues](https://img.shields.io/github/issues/Bishoko/Bishokus.svg?style=flat-square)](https://github.com/Bishoko/Bishokus/issues)
  [![Discord](https://img.shields.io/discord/391919052563546112?style=flat-square&logo=Discord&logoColor=fff&label=Join%20Discord&color=5e6ae8&link=https%3A%2F%2Fdiscord.gg%2FuZhDuyWyRh)](https://discord.gg/uZhDuyWyRh)

</div>

---

## ✨ About

Originally developed by [Lenoch](https://github.com/Lenochxd), the bot was rewritten to improve functionality and maintainability.

**Built with:** [Nextcord](https://github.com/nextcord/nextcord) | **Data Storage:** MySQL

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [⚙️ Dev Setup](#️-dev-setup)
  - [🐧 Linux Setup](#setup-for-linux)
  - [🪟 Windows Setup](#setup-for-windows)
- [🤝 Contributing](#-contributing)
- [💬 Support](#-support)

---

## 🚀 Quick Start

### Add Bishokus to Your Server

**[➕ Add Bishokus to Your Server](https://discord.com/api/oauth2/authorize?client_id=854081099638112256&permissions=277582703681&scope=bot%20applications.commands)**

Once added, use `/help` to see all available commands!

---

## 🤝 Contributing

Have ideas or found a bug? We'd love to hear from you!

**[📝 Submit Suggestions & Bug Reports](https://github.com/Bishoko/Bishokus/issues/new/choose)**

All feedback is appreciated and will be considered.

<br>

---

## ⚙️ Dev Setup

### Setup for Linux

#### 🐍 Setup Python

1. **Install Python** using your package manager:
   ```sh
   sudo apt update
   sudo apt install python3 python3-venv python3-pip
   ```

2. **Create & Activate Virtual Environment:**
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```sh
   # Install nextcord (Discord library)
   git clone -b components_v2 https://github.com/alentoghostflame/nextcord
   cd nextcord
   POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.1 pip install .
   cd ..
   
   # Install other requirements
   pip install -r requirements.txt
   ```

#### 🗄️ Setup MySQL

1. **Install MySQL:**
   ```sh
   sudo apt update
   sudo apt install mysql-server
   ```

2. **Start MySQL Service:**
   ```sh
   sudo systemctl start mysql
   sudo systemctl enable mysql
   ```

3. **Secure MySQL Installation:**
   ```sh
   sudo mysql_secure_installation
   ```

4. **Create Database & User:**
   ```sh
   sudo mysql -u root -p
   ```
   
   ```sql
   CREATE DATABASE your_database_name;
   CREATE USER 'your_username'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'your_password';
   GRANT ALL PRIVILEGES ON your_database_name.* TO 'your_username'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

#### 🔧 Configure Application

1. Open `config/config.json`
2. Update with your database credentials and Discord bot token
3. Reference `config/config.example.json` for the structure

---

### Setup for Windows

#### 🐍 Setup Python

1. **Install Python:**
   - Download from [python.org](https://www.python.org/downloads/)
   - Run the installer and ensure **"Add Python to PATH"** is checked

2. **Create & Activate Virtual Environment:**
   ```batch
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```

3. **Install Dependencies:**
   ```powershell
   # Install nextcord (Discord library)
   git clone -b components_v2 https://github.com/alentoghostflame/nextcord
   cd nextcord
   $env:POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1"
   pip install .
   cd ..
   
   # Install other requirements
   pip install -r requirements.txt
   ```

#### 🗄️ Setup MySQL

1. **Install MySQL:**
   - Download [MySQL Installer Community](https://dev.mysql.com/get/Downloads/MySQLInstaller/mysql-installer-community-8.0.37.0.msi)
   - Run the installer and follow the setup wizard

2. **Create Database & User:**
   
   **Option 1:** Using MySQL CLI
   ```batch
   mysql -u root -p --port 3306
   ```
   
   Then run:
   ```sql
   CREATE DATABASE your_database_name;
   CREATE USER 'your_username'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'your_password';
   GRANT ALL PRIVILEGES ON your_database_name.* TO 'your_username'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```
   
   **Option 2:** Use the MySQL Installer GUI to create the database interactively

#### 🔧 Configure Application

1. Open `config/config.json`
2. Update with your database credentials and Discord bot token
3. Reference `config/config.example.json` for the structure

---

## 💬 Support

- **Discord Community:** [Join our Discord](https://discord.gg/uZhDuyWyRh)
- **Issues & Bugs:** [GitHub Issues](https://github.com/Bishoko/Bishokus/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Bishoko/Bishokus/discussions)

---

<div align="center">

Made with ❤️ by the Bishokus community

[⬆ Back to Top](#-bishokus)

</div>
