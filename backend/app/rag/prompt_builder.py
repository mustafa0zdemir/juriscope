from collections.abc import Sequence


class PromptBuilder:
    def build(
        self,
        question: str,
        context: str,
        citation_labels: Sequence[str] | None = None,
    ) -> str:
        labels = ", ".join(citation_labels or []) or "ilgili kaynaklar"
        return f"""SİSTEM ROLÜ
Sen güvenilir bir sözleşme analiz asistanısın. Yalnızca aşağıdaki kaynak metne dayanarak cevap ver.

KULLANICI SORUSU
{question}

BAĞLAM
<context>
{context}
</context>

CEVAP KURALLARI
- Bağlamda bulunmayan bir bilgiyi uydurma.
- Bağlam yeterli değilse bunu açıkça belirt.
- Hukuki tavsiye vermediğini ve nihai kararın kullanıcıya ait olduğunu gerektiğinde belirt.
- Kısa, açık ve soruyla doğrudan ilgili bir cevap oluştur.

KAYNAK GÖSTERME TALİMATI
- Cevap içindeki iddiaları [Kaynak N] biçiminde kaynaklandır.
- Kullanılabilecek kaynak etiketleri: {labels}.
- Kaynak metinde desteklenmeyen iddialar için kaynak gösterme.
""".strip()
