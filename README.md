# Sözleşme Analizi Sistemi

Production-ready sözleşme analizi platformu. Backend FastAPI, frontend React + Vite ile geliştirilmektedir.

## Gereksinimler

- Docker & Docker Compose
- Node.js 18+
- Python 3.13+ (lokal backend geliştirmesi için)

---

## Servisleri Başlatma

```bash
# Tüm backend servislerini başlat (backend + postgres + minio)
docker-compose up -d --build

# Servis loglarını izle
docker-compose logs -f

# Servisleri durdur
docker-compose down
```

---

## MinIO Object Storage

Yüklenen sözleşme dosyaları MinIO üzerinde saklanır.

### MinIO Yönetim Konsolu

URL: `http://localhost:9001` — Kullanıcı: `minioadmin` / Şifre: `minioadmin`

### Bucket Yapısı

Uygulama ilk başladığında `contracts` bucket'ı otomatik oluşturulur.

```
contracts/
  └── 2026/
        └── 07/
              └── <uuid>.pdf     (storage_key formatı)
```

### Chunking Pipeline
* **ChunkStrategy**: Open/Closed prensibi ile `FixedSizeChunkStrategy` eklendi (1000 kar, 200 overlap).
* **DocumentChunk**: Her chunk veritabanında index, token_count ve metadata ile tutuluyor.
* **Metadata**: Start/end karakter pozisyonları, sayfa, dil, strateji gibi zengin metadata (JSONB).

### Document Processing Pipeline

* **Background Tasks**: FastAPI `BackgroundTasks` ile asenkron PDF/DOCX işleme
* **Document Parser Mimarısi**: PyMuPDF ve python-docx ile abstraction üzerinden metin çıkarma
* **DocumentContent**: Çıkarılan metinlerin ilişkisel veritabanında saklanması
* **Status Yönetimi**: `uploaded` -> `parsing` -> `parsed` | `failed` durum makinesi
* **Storage**: MinIO provider üzerinden dosya çekme

### Upload Akışı

```
İstek → JWT Doğrulama → Dosya Validasyonu (tip + boyut)
    → UUID oluşturma → MinIO'ya yükleme → DB kaydı → Response
```

---

## Database Migration


### Migration Çalıştırma (Tüm migration'ları uygula)

```bash
docker-compose exec backend alembic upgrade head
```

### Migration Oluşturma (Yeni bir değişiklik sonrası)

```bash
docker-compose exec backend alembic revision --autogenerate -m "açıklama"
```

### Belirli Bir Revision'a Gitme

```bash
docker-compose exec backend alembic upgrade <revision_id>
docker-compose exec backend alembic downgrade <revision_id>
```

### Veritabanını Sıfırlama

```bash
# Tüm migration'ları geri al
docker-compose exec backend alembic downgrade base

# Tekrar uygula
docker-compose exec backend alembic upgrade head
```

### Migration Geçmişini Görme

```bash
docker-compose exec backend alembic history --verbose
docker-compose exec backend alembic current
```

---

## Seed Kullanıcısı

İlk migration (`001_create_users_table`) çalıştırıldığında otomatik olarak aşağıdaki admin kullanıcısı oluşturulur:

| Alan     | Değer               |
|----------|---------------------|
| username | `admin`             |
| email    | `admin@example.com` |
| password | `admin123`          |

Şifre bcrypt ile hashlenmiş olarak veritabanında saklanır.

---

## Frontend (Lokal)

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

---

## API Dokümantasyonu

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Endpoint'ler

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/health` | Servis durum kontrolü |
| POST | `/api/v1/auth/login` | JWT token al |
| GET | `/api/v1/auth/me` | Giriş yapan kullanıcı bilgisi |
| POST | `/api/v1/upload` | Dosya yükleme (PDF, DOC, DOCX) → MinIO |
| GET | `/api/v1/contracts` | Kullanıcının sözleşmelerini listele |
| GET | `/api/v1/contracts/{id}` | Tek sözleşme detayını getir |
| GET | `/api/v1/contracts/{id}/content` | Sözleşme içeriğini getir |
| GET | `/api/v1/contracts/{id}/content` | Sözleşme içeriğini getir |
| GET | `/api/v1/contracts/{id}/status` | İşleme durumunu getir |
| GET | `/api/v1/contracts/{id}/chunks` | Sözleşmeye ait chunk'ları listele |
| GET | `/api/v1/contracts/{id}/chunks/{chunk_id}` | Belirli chunk detayını getir |
| GET | `/api/v1/contracts/{id}/download` | Dosyayı MinIO'dan indir |
| DELETE | `/api/v1/contracts/{id}` | Sözleşmeyi ve MinIO dosyasını sil |

---

## Proje Yapısı

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # Endpoint'ler
│   │   ├── config/             # Uygulama ayarları
│   │   ├── core/               # Security, exceptions
│   │   ├── database/           # Engine, session, base
│   │   ├── dependencies/       # FastAPI Depends()
│   │   ├── middleware/
│   │   ├── models/             # SQLAlchemy ORM modelleri
│   │   ├── repositories/       # Veri erişim katmanı
│   │   ├── schemas/            # Pydantic request/response
│   │   └── services/           # Business logic
│   ├── alembic/                # Migration dosyaları
│   ├── uploads/                # Yüklenen dosyalar
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       ├── context/
│       ├── hooks/
│       ├── layouts/
│       ├── pages/
│       ├── router/
│       ├── services/
│       └── types/
└── docker-compose.yml
```
