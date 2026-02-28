# 🏎️ Pinewood Derby Race Day App

A single-event race management app for Cub Scout Pinewood Derby.
Hosted on **GitHub Pages**, backend on **Supabase**.

---

## Quick Setup (do this once before race day)

### 1 — Run the database schema in Supabase

1. Open your Supabase project → **SQL Editor**
2. Paste and run the entire contents of `supabase/schema.sql`

> That creates all tables, the auto car-number trigger, RLS policies,
> and the `car-images` storage bucket automatically.

### 2 — Enable Realtime on the tables

In Supabase: **Database → Replication → Tables**
Toggle **Realtime ON** for:
- `race_state`
- `heat_results`
- `heat_entries`
- `heats`
- `cars`

### 3 — Deploy to GitHub Pages

1. Push this folder to a GitHub repository.
2. Go to **Settings → Pages** → set Source to **`main` branch / `root` (`/`)**.
3. Your site will be live at `https://<you>.github.io/<repo>/`

> `config.js` already contains the Supabase URL and anon key.
> The anon key is safe to commit — Supabase RLS handles security.

---

## Race-Day Workflow

### Pre-race (check-in / inspection)

| Who | URL | What they do |
|-----|-----|--------------|
| Parents | `/` | Register car (kid name + photo) → get car number + QR code |
| Inspection staff | `/admin/inspection.html` | Scan parent QR → tap **Legal** ✅ or **Not Legal** ❌ |

### During the race

| Who | URL | What they do |
|-----|-----|--------------|
| Race master (host) | `/admin/rounds.html` | Start a round → generates all heats |
| Track setup | `/admin/track.html` | See lane assignments, tap **Next Heat** |
| Race official | `/admin/results.html` | Tap cars in finish order → Submit |
| Audience / big screen | `/display/` | Live lanes + top 6 leaderboard (auto-refresh) |

### Between rounds

1. Open `/admin/rounds.html`
2. Wait for all heats to show **done**
3. Enter how many cars advance → click **Confirm & Start Next Round**
4. The app auto-eliminates the bottom cars and generates the next round's heats

---

## Race Format

| Round | Who races | Heats |
|-------|-----------|-------|
| Round 1 | All legal cars | Each car races once per lane (N heats for N cars) |
| Round 2+ | Top N cars (host decides) | Same — each car once per lane |
| Finals | Top 4 | 4 heats, each car in each lane |

**Scoring**: 1st = 1 pt, 2nd = 2 pts, 3rd = 3 pts, 4th = 4 pts.
**Lowest total points wins.** (Heat numbers and order are locked once a round starts.)

---

## Pages Reference

```
/                        # Parent car registration + QR codes
/admin/index.html        # Admin hub (event overview)
/admin/inspection.html   # Car inspection — QR scan + Legal/Not Legal
/admin/track.html        # Track setup — current lane board + Next Heat
/admin/results.html      # Race official — enter 1st–4th finish order
/admin/rounds.html       # Host — start rounds, eliminate cars
/display/index.html      # Public TV display — live lanes + top 6
```

---

## Reset for next year

In Supabase SQL Editor, run:

```sql
TRUNCATE cars, rounds, heats, heat_entries, heat_results CASCADE;
UPDATE race_state SET current_round_id = NULL, current_heat_id = NULL;
```

Car numbers will restart from 1.

---

## Tech Stack

- **Frontend**: Vanilla HTML / CSS / JavaScript (no framework, no build step)
- **Backend**: [Supabase](https://supabase.com) (Postgres + Storage + Realtime)
- **Hosting**: GitHub Pages
- **QR Codes**: [qrcodejs](https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js)
- **QR Scanner**: [html5-qrcode](https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js)
