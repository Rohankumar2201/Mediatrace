# Contributing to MediaTrace

Thanks for taking the time to contribute! 🎉 Whether it's a bug fix, new feature, or just improving docs — all contributions are welcome.

---

## 🚀 Getting Started

### 1. Fork the repository

Click **Fork** on the top right of the GitHub page.

### 2. Clone your fork

```bash
git clone https://github.com/your-username/MediaTrace.git
cd MediaTrace
```

### 3. Create a branch

Always work on a new branch, never directly on `main`:

```bash
git checkout -b feature/your-feature-name
```

Use clear branch names like:
- `feature/batch-upload`
- `fix/threshold-bug`
- `docs/update-readme`

### 4. Set up the environment

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your YouTube API key to .env
```

### 5. Make your changes

Write clean, readable code. Add comments where the logic isn't obvious.

### 6. Test your changes

Always run the offline test before submitting:

```bash
python test_local.py
```

Make sure the output ends with:
```
✓ MATCH DETECTED — pipeline working correctly!
Correctly rejected ✓
```

### 7. Commit your changes

Write clear commit messages:

```bash
git add .
git commit -m "feat: add batch video upload support"
```

Follow this commit format:
| Prefix | When to use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes |
| `refactor:` | Code restructuring (no behavior change) |
| `test:` | Adding or updating tests |
| `chore:` | Dependency updates, config changes |

### 8. Push and open a Pull Request

```bash
git push origin feature/your-feature-name
```

Then go to GitHub and click **New Pull Request**.

---

## 🐛 Reporting Bugs

Open an [Issue](../../issues) and include:

- What you did
- What you expected to happen
- What actually happened
- Your Python version (`python --version`)
- Any terminal error output

---

## 💡 Suggesting Features

Open an [Issue](../../issues) with the label `enhancement` and describe:

- What problem it solves
- How you'd expect it to work
- Any examples or references

---

## 🔒 Security

**Never commit your `.env` file or API keys.**

If you accidentally push a secret, immediately:
1. Revoke the key in Google Cloud Console
2. Generate a new one
3. Update your `.env`

---

## 📋 Code Style

- Use clear, descriptive variable names
- Keep functions small and focused on one thing
- Add a docstring to every function
- Follow PEP 8 formatting

---

## ❤️ Thank You

Every contribution — big or small — makes MediaTrace better. We appreciate your time and effort!
