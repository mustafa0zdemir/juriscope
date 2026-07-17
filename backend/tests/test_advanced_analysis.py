from app.advanced_analysis.schemas import ClauseType, ContractComparisonRequest
from app.advanced_analysis.services.clause_detection_service import ClauseDetectionService
from app.advanced_analysis.services.comparison_service import ContractComparisonService
from app.advanced_analysis.services.compliance_service import ComplianceService
from app.models.contract import Contract
from app.models.document_chunk import DocumentChunk
from app.models.document_content import DocumentContent


def create_contract(db, user_id: int, suffix: str, texts: list[str]) -> Contract:
    contract = Contract(
        user_id=user_id,
        original_filename=f"{suffix}.pdf",
        stored_filename=f"{suffix}.pdf",
        storage_key=f"contracts/{suffix}.pdf",
        mime_type="application/pdf",
        file_size=100,
        status="embedded",
    )
    db.add(contract)
    db.flush()
    content = DocumentContent(
        contract_id=contract.id,
        extracted_text="\n".join(texts),
        page_count=1,
        parser="test",
        language="tr",
    )
    db.add(content)
    db.flush()
    db.add_all(
        DocumentChunk(
            contract_id=contract.id,
            content_id=content.id,
            chunk_index=index,
            text=text,
            page_number=1,
            token_count=len(text.split()),
            char_count=len(text),
            metadata_={},
        )
        for index, text in enumerate(texts)
    )
    db.commit()
    db.refresh(contract)
    return contract


def test_clause_detection_classifies_supported_clauses(db, current_user) -> None:
    contract = create_contract(
        db,
        current_user.id,
        "clauses",
        [
            "Gizlilik ve kişisel veri hükümleri kapsamında KVKK uygulanır.",
            "Taraflar otuz gün ihbar süresiyle fesih hakkına sahiptir.",
            "Ödeme ve teslimat on iş günü içinde tamamlanır.",
        ],
    )

    result = ClauseDetectionService().detect(db, current_user.id, contract.id)

    assert ClauseType.CONFIDENTIALITY in result.detected_types
    assert ClauseType.KVKK in result.detected_types
    assert ClauseType.TERMINATION in result.detected_types
    assert all(clause.risk_tags for clause in result.clauses)


def test_compliance_report_lists_missing_legislation_requirements(db, current_user) -> None:
    contract = create_contract(db, current_user.id, "compliance", ["Ödeme bedeli fatura tarihinden sonra ödenir."])

    report = ComplianceService().check(db, current_user.id, contract.id)

    assert report.compliance_score < 50
    assert any(finding.law == "KVKK" and ClauseType.KVKK in finding.missing_clauses for finding in report.findings)


def test_contract_comparison_finds_added_removed_and_modified_clauses(db, current_user) -> None:
    base = create_contract(
        db,
        current_user.id,
        "base",
        ["Ödeme bedeli 30 gün içinde ödenir.", "Gizlilik süresiz olarak korunur."],
    )
    comparison = create_contract(
        db,
        current_user.id,
        "comparison",
        [
            "Ödeme bedeli 7 gün içinde ve peşin ödenir.",
            "Taraflar 15 gün ihbar süresiyle fesih hakkına sahiptir.",
        ],
    )

    result = ContractComparisonService().compare(
        db,
        current_user.id,
        ContractComparisonRequest(base_contract_id=base.id, comparison_contract_id=comparison.id),
    )

    assert any(clause.clause_type is ClauseType.TERMINATION for clause in result.added_clauses)
    assert any(clause.clause_type is ClauseType.CONFIDENTIALITY for clause in result.removed_clauses)
    assert any(change.clause_type is ClauseType.PAYMENT for change in result.modified_clauses)
    assert {change.direction for change in result.risk_changes} >= {"ADDED", "REMOVED", "CHANGED"}


def test_advanced_analysis_rejects_another_users_contract(client, db, current_user) -> None:
    contract = create_contract(db, current_user.id + 100, "foreign", ["Gizlilik hükmü uygulanır."])

    clauses = client.get(f"/api/v1/contracts/{contract.id}/clauses")
    compliance = client.post(f"/api/v1/contracts/{contract.id}/compliance")

    assert clauses.status_code == 403
    assert compliance.status_code == 403


def test_advanced_analysis_endpoints(client, db, current_user) -> None:
    base = create_contract(db, current_user.id, "api-base", ["Ödeme bedeli 30 gün içinde ödenir."])
    other = create_contract(db, current_user.id, "api-other", ["Ödeme bedeli 10 gün içinde ödenir. Fesih mümkündür."])

    clauses = client.get(f"/api/v1/contracts/{base.id}/clauses")
    compliance = client.post(f"/api/v1/contracts/{base.id}/compliance")
    comparison = client.post(
        "/api/v1/contracts/compare",
        json={"base_contract_id": base.id, "comparison_contract_id": other.id},
    )

    assert clauses.status_code == 200
    assert compliance.status_code == 200
    assert comparison.status_code == 200
    assert comparison.json()["modified_clauses"]
