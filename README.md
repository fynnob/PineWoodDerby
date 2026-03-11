THIS IS THE PRIVATE VERSION FOR MY PACK USE https://github.com/fynnob/PineWoodDerby-OpenSoucre INSTEAD!

# 🏎️ Pinewood Derby Race Day App

A complete race management app for Cub Scout Pinewood Derby — built for mobile, designed for projector displays, zero installs required for parents.
Hosted on **GitHub Pages**, backend on **Supabase**.

---

## What It Does

- **Parents** register their car from their phone — enter a name, take a photo, and get a car number + QR code instantly
- **Inspection staff** scan the parent's QR code on their phone and mark each car Legal ✅ or Not Legal ❌
- **The host** starts rounds, controls which cars advance, and drives the big screen from a single page
- **Race officials** tap cars in finish order to record results — standings update live
- **The big screen** shows the current heat's lane assignments and a live leaderboard — no refresh needed
- **Optional**: parents receive a confirmation email with their check-in QR code and the 6 official inspection rules

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

> `config.js` contains the Supabase URL and anon key.
> The anon key is safe to commit — Supabase RLS handles security.

---

## Race-Day Workflow

### Pre-race (check-in / inspection)

| Who | URL | What they do |
|-----|-----|--------------|
| Parents | `/` | Register car (name + photo) → get car number + QR code |
| Inspection staff | `/admin/inspection.html` | Scan parent QR → tap **Legal** ✅ or **Not Legal** ❌ |

### During the race

| Who | URL | What they do |
|-----|-----|--------------|
| Host / Announcer | `/admin/announcer.html` | Control big screen: slides, messages, scoreboard, scroll |
| Race master | `/admin/rounds.html` | Start a round → generates all heats |
| Track setup | `/admin/track.html` | See lane assignments, tap **Next Heat** |
| Race official | `/admin/results.html` | Tap cars in finish order → Submit |
| Audience / big screen | `/display/screen.html` | Live lanes + leaderboard (auto-refresh, no touch needed) |

### Between rounds

1. Open `/admin/rounds.html`
2. Wait for all heats to show **done**
3. Enter how many cars advance → click **Confirm & Start Next Round**
4. The app auto-eliminates the bottom cars and generates the next round's heats

### Finals mode (≤ 4 cars)

When only 4 cars remain, the split screen automatically enters **suspense mode**: full-width lane cards, no standings shown, to keep the result a surprise until the final heat.

---

## Race Format

| Round | Who races | Heats |
|-------|-----------|-------|
| Round 1 | All legal cars | Each car races once per lane (N heats for N cars) |
| Round 2+ | Top N cars (host decides) | Same — each car once per lane |
| Finals | Top 4 | 4 heats, each car in each lane |

**Scoring**: 1st = 1 pt, 2nd = 2 pts, 3rd = 3 pts, 4th = 4 pts.
**Lowest total points wins.** (Heat numbers and order are locked once a round starts.)

During qualifying rounds, the leaderboard ranks by **average points per race** so cars that have run more heats aren't unfairly penalised.

---

## Pages Reference

```
/                          # Parent car registration + QR codes
/admin/index.html          # Admin hub (event overview)
/admin/inspection.html     # Car inspection — QR scan + Legal/Not Legal
/admin/track.html          # Track setup — current lane board + Next Heat
/admin/results.html        # Race official — enter 1st–4th finish order
/admin/rounds.html         # Host — start rounds, eliminate cars
/admin/cars.html           # View all registered cars + inspection status
/admin/announcer.html      # Announcer — control the big screen
/admin/settings.html       # Settings — email toggle (PIN protected)
/display/screen.html       # Public big screen — live split + scoreboard
```

---

## Big Screen Features (Announcer → `/admin/announcer.html`)

- **Message** — push a full-screen text announcement to the display
- **Color Text** — styled message with a coloured background
- **Scoreboard** — show the live points leaderboard (scrollable with ↑/↓ hold buttons)
- **Split Screen** — live lane assignments + mini standings side-by-side
- **Google Slides** — present a slideshow with Prev/Next navigation
- **Live Score** — toggle live race feed on-screen

---

## Registration Email (Optional)

Parents can optionally receive an email with:
- Their car's **check-in QR code** (for inspection day)
- The **6 official BSA inspection rules** (weight, dimensions, track clearance, wheels, body, no motors)

Enable / disable in `/admin/settings.html` (PIN: see your race administrator).

### Email Setup (one-time, already done for this deployment)

1. Install Supabase CLI: `npm i -g supabase`
2. Login: `supabase login`
3. Link project: `supabase link --project-ref <your-project-ref>`
4. Set SMTP secret: `supabase secrets set SMTP_PASSWORD=<your-smtp-password>`
5. Deploy function: `supabase functions deploy send-registration-email --no-verify-jwt`
6. Run schema update in SQL Editor (see `supabase/schema.sql`)

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
- **Backend**: [Supabase](https://supabase.com) (Postgres + Realtime + Storage + Edge Functions)
- **Hosting**: GitHub Pages
- **Email**: Supabase Edge Function (Deno) + Nodemailer + Zoho SMTP
- **QR Codes**: [qrcodejs](https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js) + [goqr.me API](https://goqr.me/api/) (for email)
- **QR Scanner**: [html5-qrcode](https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js)
