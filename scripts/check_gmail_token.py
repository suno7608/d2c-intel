#!/usr/bin/env python3
"""Gmail OAuth 토큰 유효성 체크 — 파이프라인 실행 전 호출"""
import json, sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_PATH = '/Users/soonho/.openclaw/workspace/tools/google-token.json'

try:
    with open(TOKEN_PATH) as f:
        t = json.load(f)
    
    creds = Credentials(
        t['token'],
        refresh_token=t['refresh_token'],
        token_uri=t['token_uri'],
        client_id=t['client_id'],
        client_secret=t['client_secret']
    )
    
    if not creds.valid:
        creds.refresh(Request())
        # 갱신된 토큰 저장
        t['token'] = creds.token
        if creds.expiry:
            t['expiry'] = creds.expiry.isoformat()
        with open(TOKEN_PATH, 'w') as f:
            json.dump(t, f, indent=2)
        print("TOKEN: refreshed successfully")
    else:
        print("TOKEN: valid")
    
    sys.exit(0)

except Exception as e:
    print(f"TOKEN: FAILED — {e}", file=sys.stderr)
    sys.exit(1)
