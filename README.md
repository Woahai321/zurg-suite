# 🎮 Zurg Suite 🎬
![image](https://github.com/user-attachments/assets/91a4491c-3606-4d83-a613-00c093cb1d54)

![GitHub last commit](https://img.shields.io/github/last-commit/woahai321/zurg-suite?style=for-the-badge&logo=github)
![GitHub issues](https://img.shields.io/github/issues/woahai321/zurg-suite?style=for-the-badge&logo=github)
![GitHub stars](https://img.shields.io/github/stars/woahai321/zurg-suite?style=for-the-badge&logo=github)
![GitHub release](https://img.shields.io/github/v/release/woahai321/zurg-suite?style=for-the-badge&logo=github)
![Docker](https://img.shields.io/badge/Docker-ready-blue?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
[![Website](https://img.shields.io/badge/Website-soluify.com-blue?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAABKElEQVQ4jZXTMUoDQRQG4C+7YmFhYSHYWFgIHkAQPICFhYcQBEEQxGNYWHgIC0H0BsELWFhYWAQLC2GzxSzsLrOz2f0hMDDvzXvfzLz3ZkopKKMxxrjHJc7wjjd0UgpfZRYVgbM4P2AevZzEHlZwiU5KYa8QmMUNtnCMh5TCqCR0jgF6eEQfq1jHFfbRxHFKYVQQWMQIZxjGehObeEUH7ZTCJCcYx2Ub99jGEEtYwDnWsIk2LlIK/ZzALK7RwlKsPWMppfAc/m+0UwrTnKCBHt7iZnlp5/GCVkrhKyd4wg5WYv6NTkrhNSdoRd0b2Cg0z0dOcIj9uHnePG/+t/k3wR/kyUNUdQE+UAAAAABJRU5ErkJgg==)](https://soluify.com/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/company/soluify)

---

## 🎬 Screenshot
![image](https://github.com/user-attachments/assets/ad0805fe-c377-4aa0-86c3-ec419e6080e9)

---

## 🚀 What is Zurg Suite?

A modern, secure web interface for managing and monitoring Zurg operations. This control panel provides a centralized dashboard for system administrators to control various Zurg operations through a beautiful, dark-mode UI.

Key Features:

- 🔒 Secure authentication system with customizable credentials
- 🌙 Modern dark mode UI with purple theme
- ⚡ Real-time operation feedback
- 📊 System status monitoring
- 🔄 Automated scheduling system for routine operations
- 🎬 Jellyfin integration for media management
- 🐳 Docker containerized for easy deployment

### Control Operations

- Remount Downloads
- Reboot Repair Worker
- Reboot Refresh Worker
- Reboot Worker Pool
- Jellyfin Library Scan

---

<details>
<summary>How Does It Work?</summary>

The Zurg Suite provides a centralized interface for managing your Zurg operations:

#### 1. **Secure Authentication**

The panel uses a secure authentication system with SHA-256 password hashing and session management.

#### 2. **Operation Control**

Users can perform various operations through the web interface:
- Remount downloads
- Reboot workers
- Scan Jellyfin libraries
- Monitor system status
- We use selenium in order to click the buttons and scrape the required information 

#### 3. **Automated Scheduling**

The panel includes a flexible scheduling system for routine operations:
- Configure multiple schedules
- Set custom intervals using cron expressions
- Enable/disable schedules as needed
</details>

<details>
<summary>Why Use Zurg Suite?</summary>

- **Centralized Control**: Manage all Zurg operations from one interface
- **Automated Tasks**: Set up scheduled operations for routine maintenance
- **Real-time Monitoring**: Track system status and operation results
- **Secure Access**: Protected by authentication and HTTPS support
- **Easy Deployment**: Simple setup with Docker
- In short, I found the need to remount my downloads whilst outside of my local network & needed a solution, that then got a bit out of hand.
</details>

---

## 🚀 Getting Started

You can run the Admin Panel in two ways: **Docker Compose** (Recommended) or **Manual Installation**.

### 1. **Docker Compose** (Recommended)

The quickest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/woahai321/zurg-suite.git
cd zurg-suite

# Create environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start the application
docker-compose up -d
```

The application will be available at `http://localhost:5001`

### 2. **Manual Installation**

For development or custom setups:

```bash
# Clone the repository
git clone https://github.com/woahai321/zurg-suite.git
cd zurg-suite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
npm install

# Run the application
python app.py
```

---

## 📋 Configuration

The application is configured through environment variables. See `.env.example` for all available options:

### Core Settings
- `ADMIN_USERNAME`: Admin panel login username
- `ADMIN_PASSWORD`: Admin panel login password (SHA-256 hash)
- `SECRET_KEY`: Flask secret key for session management
- `PORT`: Application port (default: 5001)

### Integration Settings
- `JELLYFIN_TOKEN`: API token for Jellyfin integration
- `JELLYFIN_HOST`: URL of your Jellyfin server
- `ZURG_HOST`: URL of your Zurg server

### Scheduling System
Each schedule is configured with:
- `ACTION`: The operation to perform
- `CRON`: Cron expression for timing
- `ENABLED`: Whether the schedule is active

Example schedules are provided in `.env.example`.

---

## 📊 Compatibility

### Media Server Integration

| Application | Status | Notes |
|:------------|:------:|:------|
| ![Jellyfin](https://img.shields.io/badge/Jellyfin-10.8.0+-blue?style=for-the-badge&logo=jellyfin) | ✅ Supported | Full functionality |
| ![Zurg](https://img.shields.io/badge/Zurg-1.0.0+-purple?style=for-the-badge&logo=github) | ✅ Supported | Full functionality |

---

## 📋 Notes

- **Security Best Practices**: Always use HTTPS in production
- **Credentials**: Keep your admin credentials secure
- **Environment Variables**: Never commit your `.env` file
- **Docker**: Use Docker for the most stable experience

## 💰 Donations

If you find this project useful and would like to support its development:

- BTC (Bitcoin): `bc1qxjpfszwvy3ty33weu6tjkr394uq30jwkysp4x0`
- ETH (Ethereum): `0xAF3ADE79B7304784049D200ea50352D1C717d7f2`

Thank you for your support!

---

## 🛠️ Troubleshooting

Common issues and solutions:

1. **Login Issues**
   - Verify your credentials in `.env`
   - Check if the server is running
   - Clear browser cache

2. **Docker Issues**
   - Check Docker logs: `docker-compose logs`
   - Verify port availability
   - Ensure proper permissions

3. **Scheduling Issues**
   - Verify cron expressions
   - Check system time
   - Review logs for errors

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Woahai321/zurg-suite&type=Date)](https://star-history.com/#Woahai321/zurg-suite&Date) 
