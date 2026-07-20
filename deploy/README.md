# Production Dağıtım Rehberi

Bu yapı frontend'i Vercel'de, backend servislerini ise tek bir Linux
sunucusunda çalıştırır. Backend, PostgreSQL, MinIO, Qdrant ve Redis internete doğrudan
açılmaz; yalnızca Caddy üzerinden FastAPI'ye HTTPS erişimi sağlanır.

## Hedef Mimari

```text
Kullanıcı -> Vercel (React)
         -> api.example.com (Caddy / HTTPS)
         -> FastAPI
         -> PostgreSQL + MinIO + Qdrant + Redis
         -> Gemini API
```

BAAI/bge-m3 ve reranker modelleri CPU/RAM kullandığı için backend Vercel'de
çalıştırılmamalıdır. En az 8 GB, önerilen 16 GB RAM ve 4 vCPU kullanılmalıdır.

## 1. Sunucu ve DNS

1. Ubuntu 24.04 sunucu oluşturun.
2. Docker Engine ve Docker Compose eklentisini kurun.
3. Güvenlik duvarında yalnızca `22`, `80` ve `443` portlarını açın.
4. `api.example.com` için sunucu IP adresine yönlenen bir `A` kaydı oluşturun.
5. Uygulama dizinini oluşturun:

```bash
sudo mkdir -p /opt/sozlesme-analizi
sudo chown "$USER":"$USER" /opt/sozlesme-analizi
```

PostgreSQL, MinIO, Qdrant ve Redis portları production compose dosyasında host'a
publish edilmez. Yönetim işlemleri `docker compose exec` veya kontrollü SSH
erişimi üzerinden yapılmalıdır.

## 2. Production Ortamı

```bash
cp deploy/.env.production.example deploy/.env.production
openssl rand -hex 64
```

Üretilen değeri `SECRET_KEY` olarak kullanın. `POSTGRES_PASSWORD`,
`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `REDIS_PASSWORD` ve `GEMINI_API_KEY` alanlarını gerçek
değerlerle doldurun. Bu dosya Git tarafından izlenmez.

`CORS_ORIGINS`, yalnızca gerçek Vercel ve özel alan adlarını içeren JSON listesi
olmalıdır:

```env
CORS_ORIGINS=["https://sozlesme.example.com","https://project.vercel.app"]
```

## 3. İlk Çalıştırma

```bash
docker compose \
  --env-file deploy/.env.production \
  --file docker-compose.production.yml \
  up --detach --build
```

Migration servisi backend başlamadan önce `alembic upgrade head` komutunu
çalıştırır. İlk açılışta Hugging Face modelleri indirileceği için sağlık
kontrolünün hazır hale gelmesi birkaç dakika sürebilir. Modeller `hf_cache`
volume'ünde saklanır ve sonraki açılışlarda yeniden indirilmez.

```bash
docker compose --env-file deploy/.env.production -f docker-compose.production.yml ps
docker compose --env-file deploy/.env.production -f docker-compose.production.yml logs -f backend
curl https://api.example.com/api/v1/health
curl https://api.example.com/api/v1/health/rag
curl https://api.example.com/api/v1/health/cache
```

## Redis Rate Limit

Redis yalnızca geçici ve dağıtık kimlik doğrulama rate-limit sayaçları için
kullanılır. Kalıcı iş verisi Redis'e yazılmaz; bu nedenle AOF/RDB persistence
kapalıdır. Backend birden fazla instance'a çıkarıldığında tüm instance'lar aynı
sayaçları kullanır. Redis kısa süreli erişilemezse `RateLimitService`, güvenlik
kontrolünü tamamen kapatmak yerine process içi sayaca geçer ve belirlenen bekleme
süresinden sonra Redis'i yeniden dener.

Production Redis servisi parola korumalıdır, yalnızca `data-network` üzerinde
erişilebilir ve 256 MB bellek sınırıyla `allkeys-lru` politikası kullanır.

## 4. Vercel Frontend

Vercel projesinde aşağıdaki ayarları kullanın:

- Root Directory: `frontend`
- Framework Preset: `Vite`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_URL=https://api.example.com/api/v1`

`frontend/vercel.json`, React Router rotalarını `index.html` dosyasına yönlendirir
ve statik asset'lere uzun süreli cache başlıkları ekler.

## 5. GitHub Actions

`Kalite Kontrolu` iş akışı backend testlerini, frontend lint/build işlemlerini ve
deployment dosyalarının sözdizimini her push ve pull request'te doğrular.
`Production Dagitimi` yalnızca GitHub Actions ekranından manuel başlatılır ve
`production` environment onayıyla sınırlandırılabilir.

Repository veya `production` environment secrets alanına şunları ekleyin:

| Secret | Açıklama |
|---|---|
| `DEPLOY_HOST` | Sunucunun IP adresi veya alan adı |
| `DEPLOY_USER` | SSH kullanıcısı |
| `DEPLOY_PATH` | `/opt/sozlesme-analizi` |
| `DEPLOY_SSH_KEY` | Deployment private SSH anahtarı |
| `DEPLOY_KNOWN_HOSTS` | Doğrulanmış sunucu host key satırı |

Host key değeri sunucunun parmak izi doğrulandıktan sonra alınmalıdır:

```bash
ssh-keyscan -H api.example.com
```

Workflow kaynak kodu rsync ile aktarır, sunucudaki
`deploy/.env.production` dosyasını korur ve Compose servislerini yeniden kurar.

## 6. Yedekleme ve Geri Dönüş

PostgreSQL yedeği:

```bash
docker compose --env-file deploy/.env.production -f docker-compose.production.yml \
  exec -T postgres pg_dump -U contract_app contract_analysis > postgres-backup.sql
```

MinIO ve Qdrant verileri Docker volume'lerinde tutulur. Sunucu sağlayıcısının disk
snapshot özelliğine ek olarak bu volume'ler düzenli olarak harici depolamaya
yedeklenmelidir. Geri dönüş için hatalı commit revert edilip `deployment`
branchine pushlandıktan sonra manuel deployment workflow'u yeniden çalıştırılır.

## Operasyon Notları

- Production gizli değerlerini repoya, Actions loglarına veya frontend env'ine koymayın.
- Gemini anahtarını yalnızca backend ortamında tutun ve periyodik olarak döndürün.
- `docker compose logs` için log rotasyonu production compose içinde aktiftir.
- Yüksek trafik oluşana kadar Redis/Kafka zorunlu değildir; belge işleme kuyruğu ayrı bir ölçekleme aşamasıdır.
