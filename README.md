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

### Retrieval Pipeline (Semantic Search)
* **Mimari**: `RetrievalProvider` soyut sınıfı, Open/Closed prensibine uygun genişletilebilir yapı.
* **QdrantRetriever**: Cosine similarity ile Qdrant üzerinde anlamsal arama.
* **Query Embedding**: Kullanıcı sorgusu aynı `BAAI/bge-m3` modeli ile embedding'e dönüştürülür.
* **Güvenlik**: Her arama isteğinde Qdrant payload filtresi ile yalnızca kullanıcının kendi sözleşmeleri döner.
* **Top-K**: Varsayılan 5, API üzerinden 1-20 arası değiştirilebilir.

```
POST /api/v1/search
    → JWT Doğrulama
    → query embedding (SentenceTransformerProvider)
    → Qdrant payload filter (contract_id in kullanıcının_sözleşmeleri)
    → Cosine similarity search
    → SearchResponse [score, chunk_id, text, metadata, ...]
```

### RAG Orchestrator (Sprint 9A)

Sprint 9A, Retrieval katmanını henüz bir LLM çağrısı yapmadan üretime hazır bir
RAG isteğine dönüştürür. `RAGService` aşağıdaki akışı orkestre eder:

```
Kullanıcı sorusu
    → RetrieverService (kullanıcı yetkili sözleşmeleri + top-k)
    → ContextBuilder (sınırlı ve kaynak etiketli context)
    → CitationBuilder (contract/chunk/page/score kaynakları)
    → PromptBuilder (LLM'e gönderilmeye hazır prompt)
```

`PromptBuilder`, sistem rolü, kullanıcı sorusu, context, cevap kuralları ve
kaynak gösterme talimatlarını merkezi olarak üretir. Context, güvenilmeyen
referans metni olarak delimiters içinde tutulur ve `ContextBuilder` tarafından
karakter limiti ile sınırlandırılır.

`CitationBuilder` her retrieval sonucu için `contract_id`, `chunk_id`,
`chunk_index`, `page_number` ve `score` alanlarını hazırlar. LLM provider
abstraction'ı `app/llm/base.py` içindeki `LLMProvider` arayüzüdür.

#### RAG API'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/v1/chat/query` | Yetkili chunk'ları getirir, context/prompt/citation üretir |
| POST | `/api/v1/chat/prompt-preview` | LLM çağrısı olmadan prompt'u önizler |

Her iki endpoint de `question`, opsiyonel `contract_ids` ve `top_k` alır.
Prompt Preview yanıtı `retrieved_chunks`, `constructed_context`,
`constructed_prompt` ve `citations` döner.

### Gemini LLM Integration (Sprint 9B)

Sprint 9B ile `GeminiProvider` ve `LLMService` eklenmiştir. RAG query akışı
şu şekildedir:

```
Semantic Retrieval
    → ContextBuilder
    → PromptBuilder
    → LLMService
    → GeminiProvider
    → CitationBuilder
    → Final Response
```

Google'ın resmi `google-genai` Python SDK'sı kullanılır. API anahtarı ve model
ayarları `backend/.env` içinde tutulmalı, örnek değerler `backend/.env.example`
dosyasındadır:

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
MAX_OUTPUT_TOKENS=1024
TEMPERATURE=0.2
TOP_P=0.95
GEMINI_TIMEOUT_SECONDS=30
```

`POST /api/v1/chat/query` artık `answer`, `citations`, `used_chunks`, `model`
ve `latency_ms` döndürür. `POST /api/v1/chat/prompt-preview` ise LLM çağrısı
yapmadan prompt önizlemesini korur. Gemini API erişilemediğinde `503`, API
anahtarı eksik olduğunda `500` döndürülür. `GET /api/v1/health/llm` Gemini
yapılandırmasının mevcut olup olmadığını gösterir; gerçek bir model çağrısı
yapmaz.

### Sohbet ve Mesaj Geçmişi 
Sisteme kalıcı sohbet (conversation) özelliği eklenmiştir. RAG üzerinden sorulan sorular ve alınan cevaplar veritabanında saklanır.
- **Conversation**: Bir sohbet oturumunu (başlık ve zaman bilgisi ile) temsil eder. `users` tablosuyla ilişkilidir.
- **ChatMessage**: Her bir sohbet içindeki mesajları (user/assistant) ve LLM meta verilerini (model, latency vb.) tutar. `conversations` tablosuyla ilişkilidir. 
- `/api/v1/chat/query` kullanıldığında; eğer istekte `conversation_id` mevcut değilse sistem otomatik olarak kullanıcının sorusuna göre bir başlık belirleyip yeni bir sohbet başlatır.

Bu mimari sayesinde eski konuşmalar listelenebilir, detaylarına bakılabilir ve sistem gelecekte eklenecek "Streaming", "Memory" veya "Chat UI" özellikleri için hazır hale getirilmiştir.

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
| GET | `/api/v1/health/llm` | Gemini yapılandırma ve model durumu |
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
| POST | `/api/v1/contracts/{id}/embed` | Chunk'ları manuel embedding işlemine al |
| GET | `/api/v1/contracts/{id}/embedding/status` | Embedding işlem durumunu getir |
| GET | `/api/v1/contracts/{id}/download` | Dosyayı MinIO'dan indir |
| DELETE | `/api/v1/contracts/{id}` | Sözleşmeyi ve MinIO dosyasını sil |
| POST | `/api/v1/search` | Vektör DB'de anlamsal arama (Semantic Search) yap |
| POST | `/api/v1/chat/query` | Retrieval context'ini Gemini ile cevaplar ve mesaja kaydeder |
| POST | `/api/v1/chat/prompt-preview` | LLM çağrısı olmadan prompt önizlemesi |
| GET | `/api/v1/conversations` | Kullanıcının tüm sohbetlerini listele |
| POST | `/api/v1/conversations` | Yeni bir sohbet oluştur |
| GET | `/api/v1/conversations/{id}` | Belirli bir sohbet detayını getir |
| GET | `/api/v1/conversations/{id}/messages` | Bir sohbetteki tüm mesajları getir |
| DELETE | `/api/v1/conversations/{id}` | Bir sohbeti ve mesajlarını sil |

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
