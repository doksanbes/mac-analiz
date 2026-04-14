# Mac Analiz - Futbol Mac Analiz Uygulamasi

Modern, koyu temali futbol mac analiz platformu.

## Kurulum

### 1. API Anahtari

Bu uygulama [football-data.org](https://www.football-data.org/) API'sini kullanir.

1. [football-data.org](https://www.football-data.org/client/register) adresinden ucretsiz kayit olun
2. API anahtarinizi alin
3. `/app/backend/.env` dosyasina anahtarinizi ekleyin:

```
FOOTBALL_DATA_API_TOKEN=buraya_api_anahtarinizi_yazin
```

### 2. Projeyi Calistirma

Backend ve frontend servisleri supervisor ile otomatik baslatilir.

- Backend: `http://localhost:8001` (FastAPI)
- Frontend: `http://localhost:3000` (Next.js)

### Teknolojiler

- **Frontend:** Next.js 14, Tailwind CSS, Lucide Icons
- **Backend:** FastAPI, httpx
- **API:** football-data.org v4

### API Endpoint'leri

- `GET /api/matches` - Gunun maclarini getirir
- `GET /api/match/{id}` - Tek mac detayini getirir
- `GET /api/health` - Sistem durumu
