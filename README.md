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
