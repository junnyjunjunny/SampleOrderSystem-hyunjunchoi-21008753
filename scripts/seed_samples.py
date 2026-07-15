import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection
from app.models import Sample
from app.repository import SampleRepository

# avg_production_time은 min/ea 단위로 저장한다. 검증(생산 라인 조회) 시 실제로 기다릴 수 있도록
# 초 단위로 0.06~0.25 sec/ea 수준이 되게 아주 작은 값(분)으로 시료마다 조금씩 다르게 잡는다.
SAMPLES = [
    Sample("S-001", "실리콘 웨이퍼-8인치", 0.0017, 0.97, 320),
    Sample("S-002", "실리콘 웨이퍼-12인치", 0.0020, 0.95, 210),
    Sample("S-003", "GaN 에피텍셜-4인치", 0.0025, 0.88, 90),
    Sample("S-004", "GaN 에피텍셜-6인치", 0.0030, 0.86, 45),
    Sample("S-005", "SiC 파워기판-6인치", 0.0033, 0.82, 60),
    Sample("S-006", "SiC 파워기판-8인치", 0.0037, 0.80, 35),
    Sample("S-007", "포토레지스트-PR7", 0.0013, 0.99, 500),
    Sample("S-008", "포토레지스트-PR9", 0.0015, 0.98, 400),
    Sample("S-009", "산화막 웨이퍼-SiO2", 0.0018, 0.94, 275),
    Sample("S-010", "질화막 웨이퍼-Si3N4", 0.0022, 0.93, 260),
    Sample("S-011", "사파이어 기판-2인치", 0.0027, 0.91, 150),
    Sample("S-012", "사파이어 기판-4인치", 0.0032, 0.89, 100),
    Sample("S-013", "게르마늄 웨이퍼-4인치", 0.0023, 0.90, 120),
    Sample("S-014", "게르마늄 웨이퍼-6인치", 0.0035, 0.87, 70),
    Sample("S-015", "실리콘 웨이퍼-6인치", 0.0017, 0.96, 340),
    Sample("S-016", "인듐인 웨이퍼-2인치", 0.0042, 0.83, 55),
    Sample("S-017", "탄탈륨 타겟-99.99%", 0.0028, 0.92, 180),
    Sample("S-018", "구리 타겟-99.999%", 0.0027, 0.93, 190),
    Sample("S-019", "알루미늄 타겟-99.9%", 0.0023, 0.94, 220),
    Sample("S-020", "포토마스크-Blank", 0.0038, 0.85, 65),
    Sample("S-021", "본딩 와이어-Au", 0.0010, 0.99, 800),
    Sample("S-022", "본딩 와이어-Cu", 0.0012, 0.98, 700),
    Sample("S-023", "리드프레임-QFN48", 0.0020, 0.95, 300),
]


def seed() -> None:
    conn = get_connection()
    repo = SampleRepository(conn)
    inserted, skipped = 0, 0
    for sample in SAMPLES:
        try:
            repo.create(sample)
            inserted += 1
        except ValueError:
            skipped += 1
    conn.close()
    print(f"시딩 완료: {inserted}건 추가, {skipped}건 이미 존재해서 건너뜀 (총 {len(SAMPLES)}건 대상)")


if __name__ == "__main__":
    seed()
