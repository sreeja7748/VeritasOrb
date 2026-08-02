# 🌍 VeritasOrbs

**VeritasOrbs** is a Flask-based graphical authentication system that replaces traditional text passwords with an ordered sequence of clicks on a map. Instead of remembering complex passwords, users authenticate by selecting predefined geographic locations.

To ensure security, the clicked locations are **snapped to configurable grid cells**, salted, and hashed using **PBKDF2-HMAC-SHA256**, meaning the original coordinates are never stored in the database.

> ⚠️ This project is intended for educational purposes and to demonstrate an alternative authentication mechanism based on geospatial input.

---
