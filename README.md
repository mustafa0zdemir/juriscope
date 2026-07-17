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

### Retrieval Pipeline (Hybrid Search)
* **Mimari**: `RetrievalProvider` soyut sınıfı, Open/Closed prensibine uygun genişletilebilir yapı.
* **QdrantRetriever**: Cosine similarity ile Qdrant üzerinde anlamsal arama.
* **BM25Service**: Yetkili sözleşmelerin `DocumentChunk.text` alanlarından bellek içi Okapi BM25 indeksi oluşturur.
* **HybridRetriever**: Vektör ve BM25 sonuçlarını normalize eder, aynı chunk'ları tekilleştirir ve re-ranking için aday havuzu oluşturur.
* **ReRankService**: Hybrid adaylarını Cross Encoder ile yeniden sıralar; yalnızca en alakalı Top-N sonucu RAG context'ine gönderir.
* **Query Embedding**: Kullanıcı sorgusu aynı `BAAI/bge-m3` modeli ile embedding'e dönüştürülür.
* **Güvenlik**: Qdrant payload filtresi ve BM25 sorgusundaki sözleşme filtresi yalnızca kullanıcının kendi belgelerini kapsar.
* **Top-K**: Varsayılan 5, API üzerinden 1-20 arası değiştirilebilir.

```
POST /api/v1/search
    → JWT Doğrulama
    → Yetkili sözleşmeleri doğrula
    → Vector Search (Qdrant) + Keyword Search (BM25)
    → Skor normalizasyonu, tekilleştirme ve Hybrid adayları
    → Cross Encoder re-ranking (opsiyonel)
    → Son Top-N sonuç
    → SearchResponse [score, chunk_id, text, metadata, ...]
```

#### Arama Modları

`search_mode` alanı `/api/v1/search`, `/api/v1/chat/query`,
`/api/v1/chat/stream` ve `/api/v1/chat/prompt-preview` isteklerinde opsiyoneldir.
Varsayılan değer `hybrid`dir.

| Mod | Davranış | Kullanım alanı |
|-----|----------|----------------|
| `vector` | Sadece Qdrant cosine similarity kullanır. | Anlamsal olarak benzer ifadeler |
| `keyword` | Sadece BM25 kelime eşleşmesi kullanır. | Madde, kanun ve karar numaraları |
| `hybrid` | İki kaynağı birleştirir, normalize eder ve tekrarları kaldırır. | Genel varsayılan arama |

Vector Search anlam bakımından yakın metinleri bulurken BM25, sorgudaki kesin
kelimeleri ve numaraları öne çıkarır. Bu birleşim özellikle hukuk metinlerindeki
`4857`, `madde 17` veya karar numarası gibi ifadelerde retrieval doğruluğunu artırır.

```env
DEFAULT_SEARCH_MODE=hybrid
ENABLE_DEBUG_SEARCH=false
```

`ENABLE_DEBUG_SEARCH=true` yapıldığında yanıtlar `vector_hits`, `keyword_hits`
`merged_hits` ve `reranked_hits` alanlarını içerir. Bu alanlardaki
`vector_score`, `bm25_score`, `hybrid_score`, `rerank_score` ve `final_rank`
bilgileri normalde kapalıdır ve üretimde yalnızca teşhis amacıyla açılmalıdır.

Örnek istek:

```json
{
  "question": "4857 sayılı Kanun'un 17. maddesindeki bildirim süresi nedir?",
  "contract_ids": [12],
  "top_k": 5,
  "search_mode": "hybrid",
  "rerank": true
}
```

### Cross Encoder Re-ranking

Hybrid Search hızlı aday üretimi yapar: Vector Search anlamsal yakınlığı, BM25
ise kesin kelime ve numara eşleşmesini ölçer. Cross Encoder ise soru ve her
aday chunk'ı birlikte değerlendirerek ilişkiyi daha yüksek doğrulukla skorlar.
Bu nedenle yalnızca Hybrid Search'ün ilk adayları üzerinde çalışır.

```
Kullanıcı sorusu
    → Embedding
    → Vector Search + BM25 Search
    → Hybrid Merge
    → İlk RERANK_INPUT_LIMIT aday (varsayılan 20)
    → BAAI/bge-reranker-v2-m3 Cross Encoder
    → RERANK_TOP_N sonuç (varsayılan 5)
    → ContextBuilder → PromptBuilder → Gemini
```

`CrossEncoderProvider`, `BAAI/bge-reranker-v2-m3` modelini yalnızca ilk aktif
re-ranking isteğinde CPU üzerinde yükler ve süreç boyunca singleton olarak
yeniden kullanır. Böylece yüzlerce MB'lık model her istek için tekrar
indirilmez veya belleğe alınmaz. Model ya da inference hatasında sistem güvenli
şekilde Hybrid Search sıralamasına geri döner; mevcut chat ve streaming akışı
kesilmez.

```env
RERANK_ENABLED=true
RERANK_MODEL=BAAI/bge-reranker-v2-m3
RERANK_INPUT_LIMIT=20
RERANK_TOP_N=5
RERANK_TIMEOUT_SECONDS=30
```

`rerank` istek alanı varsayılan olarak `true`dur. İstemci bazında performans
karşılaştırması yapmak için `false` gönderilebilir; `RERANK_ENABLED=false`
ortam ayarı ise re-ranking katmanını uygulama genelinde kapatır ve modeli hiç
yüklemez.

### Trustworthy RAG

Trustworthy RAG katmanı, mevcut Multi-Source RAG akışının önüne ve arkasına
güvenilirlik kontrolleri ekler. Retrieval, re-ranking, Gemini ve citation
mimarileri değiştirilmez; `RAGGuardService` mevcut orkestrasyona dependency
injection ile bağlanır.

```text
Question
    → Multi-Source Hybrid Retrieval
    → Retrieval Metrics
    → Context Sufficiency + Prompt Security Guardrails
    → [yeterliyse] PromptBuilder → Gemini
    → Grounding Validation
    → Citation Coverage
    → Hallucination Risk
    → Answer Confidence
```

#### Context Guardrails

LLM çağrısından önce chunk sayısı, context uzunluğu, ortalama retrieval skoru,
normalize edilmiş rerank skoru, kaynak çeşitliliği ve prompt injection kalıpları
kontrol edilir. Context yeterli veya güvenli değilse Gemini çağrılmaz. Bu durum
sistem hatası kabul edilmez ve HTTP `200` ile döner:

```json
{
  "status": "insufficient_context",
  "message": "Soruya güvenilir bir cevap üretmek için yeterli ve güvenli context bulunamadı.",
  "confidence": 0,
  "context_sufficient": false,
  "guardrails": {},
  "retrieval_metrics": {}
}
```

Streaming akışında aynı durum `guardrails` SSE eventiyle bildirilir; yarım veya
uydurulmuş assistant mesajı conversation tablosuna kaydedilmez.

#### Prompt Guardrails

`PromptBuilder` modele yalnızca verilen context'i kullanmasını, hukuki bilgi
uydurmamasını, kaynak dışı yorum ve kaynaksız iddia üretmemesini, kanıt yoksa
bunu söylemesini ve kanun/emsal karar çelişkisini açıklamasını zorunlu kılar.

#### Grounding ve Citation Validation

`GroundingValidator`; boş veya çok kısa cevap, citation kullanımı ve cevap ile
context arasındaki kelime örtüşmesini değerlendirir. Sonuç `GROUNDED`,
`PARTIALLY_GROUNDED` veya `LOW_GROUNDED` olarak döner.

`CitationCoverageValidator`, cevap içindeki doğrulanabilir iddiaları ve geçerli
`[Kaynak N]` referanslarını sayar. `total_claims`, `supported_claims`,
`unsupported_claims` ve `coverage_percent` alanlarını üretir. Legal Analysis
JSON çıktılarındaki `citation` alanları da aynı doğrulamaya dahildir.

#### Hallucination Risk ve Confidence

Hallucination riski `0-100` aralığında hesaplanır. Retrieval, rerank, citation
coverage, kaynak çeşitliliği, context uzunluğu ve grounding confidence birlikte
değerlendirilir. Risk seviyesi `LOW`, `MEDIUM` veya `HIGH` olur. Chat response
içindeki geliştirilmiş `confidence` değeri hallucination riskinin tersidir.

Chat ve Legal Analysis response'ları geriye dönük alanlarını koruyarak şu
opsiyonel metadata'yı ekler:

- `guardrails`
- `grounding`
- `citation_coverage`
- `hallucination_risk`
- `retrieval_metrics`
- `context_sufficient`

Retrieval metrics; `retrieved_chunks`, `reranked_chunks`, `used_chunks`,
`average_similarity`, `average_rerank_score`, `context_characters`,
`context_sources` ve `search_mode` değerlerini içerir.

#### Yapılandırma

```env
ENABLE_RAG_GUARDRAILS=true
ENABLE_GROUNDING_CHECK=true
ENABLE_CITATION_VALIDATION=true
ENABLE_HALLUCINATION_CHECK=true
MIN_CONTEXT_CHUNKS=1
MIN_CONTEXT_CHARACTERS=10
MIN_RETRIEVAL_SCORE=0.2
MIN_RERANK_SCORE=0.0
ENABLE_DEBUG_CHAT=false
```

Eşikler deployment ortamına ve veri setine göre yükseltilebilir. Cross Encoder
ham logitleri guardrail karşılaştırmasından önce `0-1` aralığına normalize edilir.

#### RAG Health ve Debug

```http
GET /api/v1/health/rag
```

Endpoint retrieval, reranker, guardrails, LLM ve legal search bileşenlerinin
durumunu; genel `ok` veya `degraded` sonucuyla birlikte döndürür.

```http
POST /api/v1/chat/debug
Authorization: Bearer <token>
```

Debug endpoint retrieval, rerank, context, guardrails, prompt, grounding,
citation coverage, hallucination risk ve LLM cevabını tek response içinde
gösterir. Prompt ve context hassas veri içerebildiğinden varsayılan olarak
kapalıdır; yalnızca geliştirme ortamında `ENABLE_DEBUG_CHAT=true` yapılmalıdır.
Kapalı olduğunda endpoint `404` döndürür ve production yüzeyi açılmaz.

### Legal Analysis Engine

Legal Analysis Engine, sohbet yanıtından farklı olarak tek bir sözleşmeyi
otomatik ve yapılandırılmış biçimde inceler. `LegalAnalysisService`, önce
sözleşmenin kullanıcıya ait ve `embedded` durumda olduğunu doğrular; sonra
mevcut Hybrid Search ve Cross Encoder re-ranking altyapısından yalnızca o
sözleşmeye ait kaynakları alır.

```
Sözleşme doğrulama ve yetkilendirme
    → Hybrid Search + Cross Encoder Re-ranking
    → ContextBuilder
    → AnalysisPromptBuilder
    → Gemini (yalnızca JSON)
    → AnalysisResponseParser
    → Risk puanı, bulgular, öneriler ve kaynaklar
```

`AnalysisPromptBuilder`, hukuk uzmanı rolünü, objektif değerlendirmeyi, kaynak
kullanım kurallarını, risk analizi ve sade Türkçe açıklama beklentisini merkezi
olarak tanımlar. `AnalysisResponseParser`, model cevabının zorunlu JSON
sözleşmesine uyduğunu doğrular. Model kaynak referanslarını üretse de API
citations alanı yalnızca retrieval sonucundaki doğrulanmış chunk metadata'sından
oluşturulur.

Risk puanı `0-100` arasındadır: `0-24 LOW`, `25-49 MEDIUM`, `50-74 HIGH` ve
`75-100 CRITICAL`. Analiz; riskli maddeler, eksik maddeler, belirsiz ifadeler,
tek taraflı hükümler, iyileştirme önerileri ve sade bir Türkçe özeti döndürür.

#### Analysis API

```http
POST /api/v1/contracts/{contract_id}/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "analysis_type": "full"
}
```

Örnek yanıt:

```json
{
  "analysis_type": "full",
  "summary": "Sözleşmede fesih süresine ilişkin belirsizlik bulunmaktadır.",
  "risk_score": 82,
  "risk_category": "CRITICAL",
  "confidence": 0.91,
  "risks": [],
  "missing_clauses": [],
  "ambiguous_clauses": [],
  "one_sided_clauses": [],
  "recommendations": [],
  "citations": []
}
```

Frontend'de sözleşmeler Dashboard üzerinden açılır. `/contracts/:contractId`
detay ekranındaki **Analiz Et** butonu isteği başlatır; sonuçlar Genel Özet,
Riskler, Eksik Maddeler, Belirsiz Maddeler, Tek Taraflı Maddeler, Öneriler ve
Kaynaklar sekmelerinde gösterilir. Bu endpoint streaming kullanmaz; mevcut chat
streaming akışı değişmeden korunur.

### Explainable AI Katmanı

Explainable AI katmanı, Legal Analysis Engine tarafından üretilen sonucun hangi
sözleşme maddesi, kanun ve emsal karara dayandığını şeffaf biçimde gösterir.
`ExplainableAnalysisService`, mevcut analiz çalıştırmasını ve yetkilendirilmiş
retrieval sonuçlarını yeniden kullanır; ikinci ve farklı bir retrieval zinciri
oluşturmaz.

```text
Legal Analysis + doğrulanmış retrieval sonuçları
    → ConfidenceBuilder
    → EvidenceBuilder
    → Legal Reasoning
    → RetrievalPathBuilder
    → Source Attribution
    → ExplainableAnalysisResponse
```

#### Confidence Score

Güven puanı `0-100` aralığındadır. Model güveni, retrieval skorları, Cross
Encoder rerank skorları ve sözleşme/kanun/emsal karar kaynak çeşitliliği birlikte
hesaplanır. Seviyeler `VERY_LOW`, `LOW`, `MEDIUM`, `HIGH` ve `VERY_HIGH` olarak
döndürülür. Bu puan hukuki doğruluk garantisi değil, kullanılan kanıt setinin
teknik yeterlilik göstergesidir.

#### Evidence ve Reasoning

Her risk için mümkün olduğunda sözleşme chunk'ı, kanun chunk'ı ve emsal karar
chunk'ı eşleştirilir. Evidence kaydı; sayfa, chunk, similarity, rerank skoru ve
metin özetini taşır. Reasoning alanı riskin neden önemli olduğunu, hukuki
dayanağı, emsal karar desteğini ve etkilenen sözleşme maddesini ayrı alanlarda
açıklar. Citation verileri yalnızca retrieval metadata'sından oluşturulur.

#### Retrieval Path

Her explain yanıtı aşağıdaki işlem zincirini durum ve hit sayılarıyla döndürür:

```text
Question → Contract Retrieval → Law Retrieval → Case Retrieval
         → Hybrid Merge → Re-ranking → Gemini → Answer
```

```http
POST /api/v1/contracts/{contract_id}/analysis/explain
Authorization: Bearer <token>
```

Yanıt; `analysis`, `confidence_score`, `confidence_level`, `reasoning`,
`evidence`, `retrieval_path`, `matched_articles`, `matched_cases`,
`used_contract_chunks` ve `citations` alanlarını içerir. Frontend analiz
ekranındaki Explain, Evidence, Confidence ve Retrieval Path sekmeleri bu alanları
kart, progress bar ve timeline olarak gösterir.

### Gelişmiş Sözleşme Analizi

Gelişmiş analiz katmanı, repository üzerinden okunan yetkili `DocumentChunk`
kayıtlarını servis katmanında işler. Repository yalnızca veri erişimi yapar;
madde sınıflandırma, risk etiketleme, karşılaştırma ve compliance kuralları
servislerde bulunur.

#### Clause Detection ve Risk Tagging

`ClauseDetectionService`; Gizlilik, Fesih, Cezai Şart, Mücbir Sebep, Tahkim,
Yetkili Mahkeme, Ödeme, Süre, Teslim, KVKK, Rekabet Yasağı ve Fikri Mülkiyet
maddelerini tespit eder. Her sonuç kategori, güven, eşleşen anahtar kelimeler,
sayfa/chunk bilgisi ve `Financial`, `Legal`, `Privacy`, `Commercial` veya
`Employment` risk etiketlerini içerir.

#### Compliance Checker

`ComplianceService`, tespit edilen madde kategorilerini Türk Borçlar Kanunu,
Türk Ticaret Kanunu, KVKK ve İş Kanunu kontrol setleriyle karşılaştırır. Rapor;
uyumluluk puanı, `COMPLIANT/PARTIAL/NON_COMPLIANT` durumu, eksik maddeler,
sorunlar ve iyileştirme önerileri döndürür. Otomatik rapor hukuki görüş yerine
geçmez ve uzman doğrulaması gerektirir.

#### Contract Comparison ve Version Diff

İki analize hazır sözleşme aynı kullanıcıya ait olmak şartıyla karşılaştırılır.
`ContractComparisonService`, kategori bazında eklenen, silinen, değiştirilen ve
değişmeyen maddeleri belirler; metin benzerliğini ölçer, risk değişimlerini ve
yeni hak/yükümlülük ifadelerini raporlar. Frontend'deki `/compare` ekranı iki
sözleşme seçimi ve yan yana fark kartları sunar.

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/v1/contracts/compare` | İki sözleşmenin version diff ve risk değişimini üretir |
| POST | `/api/v1/contracts/{id}/compliance` | Dört temel mevzuat için compliance raporu üretir |
| GET | `/api/v1/contracts/{id}/clauses` | Sınıflandırılmış maddeleri ve risk etiketlerini döndürür |

Karşılaştırma isteği:

```json
{
  "base_contract_id": 12,
  "comparison_contract_id": 18
}
```

Tüm endpoint'ler JWT korumalıdır. Her sözleşmenin giriş yapan kullanıcıya ait ve
`embedded` durumda olduğu servis katmanında doğrulanır.

### Legal Knowledge Base

Legal Knowledge Base; kanun, yönetmelik, tebliğ ve yüksek mahkeme kararlarını
kullanıcı sözleşmelerinden bağımsız, merkezi bir kaynak havuzunda tutar. Normal
kullanıcılar legal belge yükleyemez veya yönetemez. `/api/v1/legal` yönetim
endpointlerinin tamamı `is_admin=true` kullanıcılara açıktır; migration mevcut
`admin` hesabını otomatik olarak yönetici yapar.

Desteklenen belge türleri:

- `LAW`, `REGULATION`, `COMMUNIQUE`
- `SUPREME_COURT`, `COUNCIL_OF_STATE`, `CONSTITUTIONAL_COURT`
- `OTHER`

#### Legal Ingestion Pipeline

```text
Admin PDF/DOCX yükleme
    → MinIO legal/{document_type}/... depolama
    → Mevcut PDF/DOCX parser
    → FixedSizeChunkStrategy
    → BAAI/bge-m3 embedding
    → Qdrant legal_documents collection
    → LegalChunk metadata ve embedded durumu
```

Contract vektörleri `contracts`, legal kaynaklar `legal_documents` collection'ında
tutulur. İki collection birbirinden bağımsızdır. Legal metadata; belge türü,
başlık, resmî numara, yayın tarihi, madde, mahkeme ve karar numarasını taşır.

#### Multi-Source Retrieval

```text
Kullanıcı sorusu
    ├─ Contract Hybrid Search
    └─ Legal Vector Search + BM25
             ↓
       Ortak aday havuzu
             ↓
       Cross Encoder re-ranking
             ↓
 KULLANICI SÖZLEŞMESİ / KANUNLAR / EMSAL KARARLAR context bölümleri
             ↓
        Gemini + Legal Citation
```

Chat, streaming ve Legal Analysis varsayılan olarak bu çok kaynaklı context'i
kullanır. `ENABLE_MULTI_SOURCE_RAG=false` ile eski contract-only akışa,
`ENABLE_LEGAL_SEARCH=false` ile legal araması kapalı çalışma moduna dönülebilir.

```env
LEGAL_COLLECTION=legal_documents
ENABLE_LEGAL_SEARCH=true
ENABLE_MULTI_SOURCE_RAG=true
LEGAL_TOP_K=10
LEGAL_RERANK_TOP_N=5
```

#### Legal Management API

| Method | Endpoint | Yetki | Açıklama |
|--------|----------|-------|----------|
| POST | `/api/v1/legal/upload` | Admin | PDF/DOCX legal belge yükler ve ingestion başlatır |
| GET | `/api/v1/legal` | Admin | Legal belgeleri listeler |
| GET | `/api/v1/legal/{id}` | Admin | Legal belge detayını getirir |
| DELETE | `/api/v1/legal/{id}` | Admin | MinIO, Qdrant ve veritabanından legal belgeyi siler |

Frontend'deki `/legal-kb` ekranı yalnızca admin kullanıcıya gösterilir. Bu
ekrandan belge yükleme, listeleme, detay görüntüleme ve silme yapılabilir.

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
ve `latency_ms` döndürür. Arama akışı varsayılan olarak Hybrid Search kullanır;
istekte `search_mode` ile `vector`, `keyword` veya `hybrid` seçilebilir.
`POST /api/v1/chat/prompt-preview` ise LLM çağrısı yapmadan prompt önizlemesini
korur. Gemini API erişilemediğinde `503`, API
anahtarı eksik olduğunda `500` döndürülür. `GET /api/v1/health/llm` Gemini
yapılandırmasının mevcut olup olmadığını gösterir; gerçek bir model çağrısı
yapmaz.

### Sohbet ve Mesaj Geçmişi 
Sisteme kalıcı sohbet (conversation) özelliği eklenmiştir. RAG üzerinden sorulan sorular ve alınan cevaplar veritabanında saklanır.
- **Conversation**: Bir sohbet oturumunu (başlık ve zaman bilgisi ile) temsil eder. `users` tablosuyla ilişkilidir.
- **ChatMessage**: Her bir sohbet içindeki mesajları (user/assistant) ve LLM meta verilerini (model, latency vb.) tutar. `conversations` tablosuyla ilişkilidir. 
- `/api/v1/chat/query` kullanıldığında; eğer istekte `conversation_id` mevcut değilse sistem otomatik olarak kullanıcının sorusuna göre bir başlık belirleyip yeni bir sohbet başlatır.

Bu mimari sayesinde eski konuşmalar listelenebilir, detaylarına bakılabilir ve streaming chat arayüzüyle birlikte kullanılabilir.

### Streaming Chat ve React Arayüzü

Sprint 11 ile gerçek zamanlı sohbet deneyimi eklenmiştir. `/chat` ekranında
conversation listesi, geçmiş mesajlar, Markdown cevaplar ve citation kartları
görüntülenir. Kullanıcı yeni sohbet oluşturabilir, sohbet silebilir, geçmişi
açabilir, cevabı kopyalayabilir veya üretimi durdurabilir.

Streaming akışı:

```
JWT + soru
    → POST /api/v1/chat/stream
    → Retriever / ContextBuilder / PromptBuilder
    → GeminiProvider.generate_content_stream
    → SSE: start → token* → citations → done
    → Tamamlanan assistant mesajının kaydedilmesi
```

SSE sırasında hata oluşursa `error` eventi gönderilir. Kullanıcı bağlantıyı
kapatır veya üretimi durdurursa yarım assistant cevabı veritabanına yazılmaz.
Tamamlanan assistant mesajları citation bilgileriyle birlikte saklanır.

Frontend streaming için `frontend/src/services/chatStream.ts`, state ve API
orkestrasyonu için `frontend/src/hooks/useChat.ts` kullanır. Markdown ve GFM
tabloları `react-markdown` ve `remark-gfm` ile render edilir.

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

## Kurumsal Frontend Mimarisi

React ve TypeScript arayüzü, hukuk ekiplerinin yoğun çalışma akışlarına uygun
beyaz zemin ve kırmızı vurgu renklerinden oluşan erişilebilir bir tasarım sistemi
kullanır. Arayüzde gradient, glassmorphism ve gereksiz gölge efektleri yerine net
hiyerarşi, güçlü kontrast ve tutarlı boşluklar tercih edilir.

- `MainLayout`, sabit kurumsal sidebar, üst navigasyon ve kaydırılabilir ana içerik alanını yönetir.
- `components/ui`, Button, Card, Badge, StatCard, EmptyState, Skeleton, SectionHeader ve ortak ikonları merkezi olarak sunar.
- Dashboard; sözleşme metriklerini, hızlı işlemleri, son sözleşmeleri ve sistem durumunu tek ekranda toplar.
- Chat; conversation sidebar, gerçek zamanlı cevap, Markdown/GFM, citation kartları, retry, copy ve generation durdurma akışlarını korur.
- Sözleşme detay ekranı; özet, risk, açıklanabilirlik, evidence, compliance, clause, kaynak, confidence ve retrieval path sekmelerini birleştirir.
- Legal Knowledge Base; admin yükleme, arama, tür filtresi, sayfalama, detay görüntüleme ve silme işlemlerini sunar.
- API ve state orkestrasyonu componentlerden ayrılarak `hooks` ve `services` katmanlarında tutulur.

Tüm ekranlar klavye odağı, okunabilir form etiketleri ve mobil/tablet kırılımları
dikkate alınarak responsive hazırlanmıştır. Tema değişikliği yalnızca sunum
katmanındadır; backend endpointleri, RAG akışı ve veri modelleri değiştirilmemiştir.

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
| POST | `/api/v1/contracts/{id}/analyze` | Sözleşme için yapılandırılmış hukuki analiz üret |
| POST | `/api/v1/legal/upload` | Admin olarak legal belge yükle ve ingestion başlat |
| GET | `/api/v1/legal` | Admin olarak legal belgeleri listele |
| GET | `/api/v1/legal/{id}` | Admin olarak legal belge detayını getir |
| DELETE | `/api/v1/legal/{id}` | Admin olarak legal belgeyi sil |
| POST | `/api/v1/search` | Vector, keyword veya hybrid sözleşme araması yap |
| POST | `/api/v1/chat/query` | Hybrid retrieval context'ini Gemini ile cevaplar ve mesaja kaydeder |
| POST | `/api/v1/chat/stream` | Hybrid retrieval sonrası Gemini cevabını SSE ile parça parça döndürür |
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
