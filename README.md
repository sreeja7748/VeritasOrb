# 🌍 VeritasOrbs

**VeritasOrbs** is a Flask-based graphical authentication system that replaces traditional text passwords with an ordered sequence of clicks on a map. Instead of remembering complex passwords, users authenticate by selecting predefined geographic locations.

To ensure security, the clicked locations are **snapped to configurable grid cells**, salted, and hashed using **PBKDF2-HMAC-SHA256**, meaning the original coordinates are never stored in the database.

> ⚠️ This project is intended for educational purposes and to demonstrate an alternative authentication mechanism based on geospatial input.

---

## ✨ Features

- 🌍 Map-based graphical authentication
- 📍 Ordered location-click password system
- 🔒 PBKDF2-HMAC-SHA256 password hashing
- 🧂 Random salt generation for every user
- 📐 Grid-based tolerance for user-friendly authentication
- 🚫 Login rate limiting and temporary account lockout
- 💾 SQLite database for secure credential storage
- ⚡ Fast Flask backend with interactive web interface

---

## 🛠️ Tech Stack

- Python 3
- Flask
- SQLite
- HTML5
- CSS3
- JavaScript
- Leaflet.js (Interactive Maps)

---

## 📂 Project Structure

```
VeritasOrbs/
│
├── app.py
├── requirements.txt
├── geodesic_auth.db
├── static/
├── templates/
└── README.md
```

---


## 🚀 Installation

### Clone the repository

```bash
git clone https://github.com/your-username/VeritasOrbs.git
cd VeritasOrbs
```

### Create a virtual environment (Optional)

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000
```

---

## 🔐 How It Works

1. A user selects an ordered sequence of locations on the interactive map.
2. Each coordinate is snapped to a configurable tolerance grid.
3. The sequence is serialized and combined with a unique random salt.
4. The data is hashed using **PBKDF2-HMAC-SHA256**.
5. During login, the clicked sequence undergoes the same process and the hashes are securely compared.
6. Multiple failed login attempts trigger temporary account lockout.

---

## 🔒 Security Features

- PBKDF2-HMAC-SHA256 hashing
- Unique salt per user
- Constant-time hash comparison
- Grid-based tolerance matching
- Rate limiting
- Temporary account lockout
- No raw geographic coordinates stored

---

## 🎯 Future Enhancements

- Multi-factor authentication (MFA)
- PostgreSQL/MySQL support
- User profile management
- Configurable authentication policies
- Adaptive grid sizing
- Interactive security analytics dashboard

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch

```bash
git checkout -b feature-name
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push your branch

```bash
git push origin feature-name
```

5. Open a Pull Request.

---


## 📜 License

This project is released for educational and research purposes. Feel free to use, modify, and extend it with appropriate attribution.

---

## 👩‍💻 Author

Developed as a cybersecurity project exploring secure alternatives to traditional password-based authentication using geographic interaction and modern cryptographic techniques.
