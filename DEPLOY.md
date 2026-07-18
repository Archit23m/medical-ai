# Making this a public website

You have a full Flask app here. To let *anyone* on the internet reach it,
deploy it to a free hosting platform — no server management needed.

## Option A: Render.com (recommended, free tier, easiest)

1. Create a free account at render.com.
2. Push this folder to a new GitHub repo (or use Render's "Upload" option
   if you don't want to use Git).
3. On Render: **New +** → **Web Service** → connect your repo.
4. Settings:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
5. Under **Environment**, add a variable:
   - Key: `ANTHROPIC_API_KEY`
   - Value: your key from console.anthropic.com
6. Click **Create Web Service**. Render gives you a public URL like
   `https://your-app.onrender.com` within a couple of minutes.
7. Share that URL with anyone — the site is now live.

Free tier note: the app "sleeps" after inactivity and takes ~30s to wake
on the next visit. Fine for a demo; upgrade to a paid instance ($7/mo) to
keep it always-on.

## Option B: Railway.app

Same idea as Render: connect the repo, set `ANTHROPIC_API_KEY` as an
environment variable, Railway auto-detects the Procfile and deploys.

## Option C: Fly.io

More control (Docker-based), still has a free allowance. Good if you
outgrow Render/Railway's free tier.

## Before going live — things to add for a real public site

1. **Rate limiting.** Anyone in the world can currently hit `/api/analyze`
   as many times as they want, which runs up your API bill. Add
   `flask-limiter` and cap requests per IP (e.g. 10/hour).
2. **A ToS / medical disclaimer page**, linked from the footer — not just
   the inline text. Strongly recommended before public launch given the
   subject matter.
3. **Don't commit your API key** to GitHub. Keep it only in the hosting
   platform's environment variable settings (`.gitignore` should exclude
   any `.env` file if you use one locally).
4. **HTTPS** — Render/Railway give you this automatically.
5. Consider **logging/monitoring** (e.g. Sentry) so you know if the app
   errors out for users.

I can help implement rate limiting and the ToS page now if you'd like —
just say so.
