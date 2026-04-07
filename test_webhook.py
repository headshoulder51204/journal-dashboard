import requests
import json

url = "http://localhost:8000/api/webhook/analysis"
payload = {
    "title": "TEST-JSON-OBJ-001",
    "host": "localhost",
    "log_file": "/var/log/syslog",
    "since": "2024-10-25 14:00:01",
    "until": "2024-10-25 14:00:01",
    "unit": "minute",
    "model": "GPT-4o",
    "tokens_used": 1000,
    "chunks_analyzed": 10,
    "total_lines": 1000,
    "match_count": 100,
    "log_hash": "",
    "created_at": "2024-10-25 14:00:01",
    "analysis": "## 인시던트 상세 분석 리포트\n\n**원인 분석**\n현재 시스템의 DB 연결 요청이 임계치를 초과하였습니다. 이는 특정 시간대의 프로모션 트래픽 유입에 따른 것으로 판단됩니다.\n\n**조치 사항**\n1. 커넥션 풀을 20에서 100으로 증설 완료.\n2. 슬로우 쿼리 로그를 기반으로 인덱스 재구성 예정."
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")
