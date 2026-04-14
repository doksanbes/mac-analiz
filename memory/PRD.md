# Maç Analiz - PRD

## Problem Statement
Turkish football match analysis app with dark theme (grey + green accents). Lists today's matches, match detail page. Uses football-data.org API. No auth/payments/betting/AI.

## Architecture
- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + Lucide Icons (port 3000)
- **Backend**: FastAPI + httpx (port 8001)
- **API**: football-data.org v4

## User Personas
- Football fans who want to track today's matches
- Turkish-speaking users needing match analysis data

## Core Requirements
- Dark theme with green accents
- All UI text in Turkish
- Home page: today's match list in cards
- Match Detail page: team info, score, status, analysis placeholders
- Loading/Error/Empty states
- Mobile responsive
- API key via environment variable only

## What's Been Implemented (Jan 2026)
- [x] FastAPI backend with /api/matches, /api/match/{id}, /api/health
- [x] Next.js frontend with App Router
- [x] Home page with hero section + match card grid
- [x] Match detail page with scoreboard + info cards + analysis placeholders
- [x] Turkish text with proper diacritical marks
- [x] Dark theme (#0A0A0A base, #141415 cards, #10B981 accent)
- [x] football-data.org API integration working with live data
- [x] Error state with Turkish message when API key not configured
- [x] Loading skeleton cards + empty state
- [x] Mobile responsive design
- [x] Glassmorphism header + stadium background hero
- [x] Staggered card animations
- [x] dotenv loading for environment variables
- [x] Minimal requirements.txt (fastapi, uvicorn, httpx, python-dotenv)

- [x] Analysis system: 5 data-driven cards (Maç Özeti, KG Analizi, Gol Analizi, MS Eğilimi, Risk Notu)
- [x] Real stats: last 15 matches, KG/Üst percentages, form strings, W-D-L records
- [x] Head-to-head data integration
- [x] Two-legged tie detection (Champions League knockout)
- [x] In-memory cache (120s TTL) for API rate limiting
- [x] Backend /api/match/{id}/analysis endpoint with parallel data fetching

## API Endpoints
- GET /api/health - System status
- GET /api/matches - Today's matches
- GET /api/match/{id} - Single match detail
- GET /api/match/{id}/analysis - Rule-based match analysis (4 cards)

## Setup
1. Get API key from football-data.org
2. Add to /app/backend/.env: FOOTBALL_DATA_API_TOKEN=your_key

## Backlog
- P0: None (MVP complete)
- P1: Live score auto-refresh, match statistics display
- P2: League filtering, search functionality
- P3: Match prediction/analysis content, historical data
