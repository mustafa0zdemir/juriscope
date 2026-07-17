import json


class AnalysisPromptBuilder:
    """Sözleşme analizi için JSON-only Gemini prompt'unu üretir."""

    def build(self, context: str, citation_count: int) -> str:
        response_contract = {
            "summary": "Avukat olmayan kişilerin anlayacağı sade Türkçe özet",
            "risk_score": "0 ile 100 arasında tam sayı",
            "confidence": "0 ile 1 arasında sayı",
            "risks": [
                {
                    "title": "risk başlığı",
                    "description": "risk açıklaması",
                    "severity": "LOW | MEDIUM | HIGH | CRITICAL",
                    "reason": "hukuki gerekçe",
                    "citation": "Kaynak numarası veya null",
                }
            ],
            "missing_clauses": [{"title": "madde", "description": "eksiklik", "citation": None}],
            "ambiguous_clauses": [{"title": "ifade", "description": "belirsizlik", "citation": None}],
            "one_sided_clauses": [{"title": "madde", "description": "dengesizlik", "citation": None}],
            "recommendations": [
                {"title": "öneri", "description": "iyileştirme", "related_risk": "risk başlığı veya null"}
            ],
            "citations": ["kullanılan kaynak numaraları"],
        }
        return f"""SİSTEM ROLÜ
Sen Türkiye'deki sözleşmeleri objektif biçimde inceleyen kıdemli bir hukuk uzmanısın.
Bu analiz hukuki tavsiye yerine geçmez; yalnızca sözleşme metnindeki riskleri ve
iyileştirme alanlarını açıklar.

GÖREV
Verilen sözleşme kaynaklarını incele. Riskleri madde bazında tespit et; KVKK,
mücbir sebep, gizlilik, uyuşmazlık çözümü ve yetkili mahkeme gibi eksik olabilecek
maddeleri değerlendir. "Makul süre", "gerekli görüldüğünde" ve "uygun şartlarda"
gibi belirsiz ifadeleri; taraflardan birini orantısız koruyan hükümleri ayrıca belirt.
Önce kullanıcı sözleşmesini, ardından ilgili mevzuatı ve son olarak emsal kararları
değerlendir. Sözleşme ile mevzuat çelişiyorsa bunu açıkça belirt.

KAYNAK KULLANIM KURALLARI
- Yalnızca aşağıdaki kaynaklardaki bilgiye dayan.
- Kaynak numaraları 1 ile {citation_count} arasındadır.
- Her risk veya bulgu için mümkünse ilgili kaynak numarasını `citation` alanında kullan.
- Kaynakta bulunmayan bir hükmü varmış gibi yazma; belirsizliği açıkça belirt.

CEVAP KURALLARI
- Sade, anlaşılır Türkçe kullan.
- Risk puanı 0-100 arasında tam sayı olsun; 0 düşük, 100 kritik risktir.
- `confidence` alanı 0-1 arasında sayı olsun.
- Tüm zorunlu alanları, bulgu yoksa boş liste olarak döndür.
- Markdown, açıklama veya kod bloğu ekleme; yalnızca geçerli JSON döndür.

JSON ŞEMASI
{json.dumps(response_contract, ensure_ascii=False)}

SÖZLEŞME KAYNAKLARI
<CONTRACT_CONTEXT>
{context}
</CONTRACT_CONTEXT>
"""
