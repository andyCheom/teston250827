# -*- coding: utf-8 -*-
"""
Firebase 전체 덤프 (Python, ADC 지원)

기능
- Firestore: 모든 루트 컬렉션을 순회하여 문서 + 서브컬렉션까지 재귀적으로 JSON 저장
- Realtime Database: --rtdb-url 주어지면 지정 경로(--rtdb-path, 기본 "/")를 JSON 저장
- 매니페스트(manifest.json)와 옵션에 따라 zip 생성

사전 준비
    pip install firebase-admin google-cloud-firestore
    gcloud auth application-default login
    gcloud config set project <PROJECT_ID>

사용 예
    # Firestore 전부 + RTDB 루트 덤프, ZIP까지 생성
    python firebase_dump_all.py \
      --project sampleprojects-468223 \
      --out-dir dump_all \
      --rtdb-url https://<YOUR_DB>.firebaseio.com \
      --rtdb-path / \
      --zip

    # Firestore만 덤프
    python firebase_dump_all.py --project sampleprojects-468223 --out-dir dump_fs_only
"""
import os, json, argparse, datetime
from typing import Dict, Any, List

import firebase_admin
from firebase_admin import credentials, db as rtdb
from google.cloud import firestore





def json_default(o):
    # Datetime (incl. DatetimeWithNanoseconds)
    if isinstance(o, datetime.datetime):
        # UTC ISO8601 (Z)로 통일
        if o.tzinfo is None:
            return o.isoformat()
        return o.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(o, (datetime.date, datetime.time)):
        return o.isoformat()

    # Bytes / Blob
    if isinstance(o, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(o)).decode("ascii")

    # Decimal
    if isinstance(o, decimal.Decimal):
        # 필요에 따라 float 또는 str 선택
        return float(o)

    # Firestore DocumentReference (duck-typing)
    if hasattr(o, "path") and hasattr(o, "id") and hasattr(o, "get"):
        return {"__type__": "document_ref", "path": o.path}

    # GeoPoint (duck-typing)
    if hasattr(o, "latitude") and hasattr(o, "longitude"):
        try:
            return {"__type__": "geo_point", "lat": float(o.latitude), "lng": float(o.longitude)}
        except Exception:
            return {"__type__": "geo_point", "lat": o.latitude, "lng": o.longitude}

    # set/frozenset
    if isinstance(o, (set, frozenset)):
        return list(o)

    # Fallback
    return str(o)

# ---------- Firestore export ----------

def fs_serialize_document(doc_snap) -> Dict[str, Any]:
    return {
        "id": doc_snap.id,
        "path": doc_snap.reference.path,
        "fields": doc_snap.to_dict() or {},
        "subcollections": {}
    }

def fs_export_subcollections(doc_ref, depth=0, max_depth=10):
    result = {}
    if depth >= max_depth:
        return result
    for subcol in doc_ref.collections():
        sub_docs = []
        for sub_doc in subcol.stream():
            node = fs_serialize_document(sub_doc)
            node["subcollections"] = fs_export_subcollections(sub_doc.reference, depth+1, max_depth)
            sub_docs.append(node)
        result[subcol.id] = sub_docs
    return result

def fs_export_collection(db, collection_name: str, max_depth=10) -> List[Dict[str, Any]]:
    coll = db.collection(collection_name)
    docs = []
    for doc in coll.stream():
        node = fs_serialize_document(doc)
        node["subcollections"] = fs_export_subcollections(doc.reference, depth=0, max_depth=max_depth)
        docs.append(node)
    return docs

def fs_export_all(db, out_dir: str, collections: List[str]=None, max_depth:int=10):
    os.makedirs(out_dir, exist_ok=True)
    if collections:
        root_colls = collections
    else:
        root_colls = [c.id for c in db.collections()]

    results = []
    for col_name in root_colls:
        print(f"[FS] exporting collection: {col_name}")
        docs = fs_export_collection(db, col_name, max_depth=max_depth)
        out_path = os.path.join(out_dir, f"{col_name}.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            import json as _json
            _json.dump(docs, f, ensure_ascii=False, indent=2, default=json_default)
        print(f"[FS][OK] wrote {out_path} ({len(docs)} docs)")
        results.append({"collection": col_name, "path": out_path, "count": len(docs)})
    return results

# ---------- RTDB export ----------

def rtdb_export(url: str, path: str, out_file: str):
    ref = rtdb.reference(path)
    data = ref.get()
    with open(out_file, 'w', encoding='utf-8') as f:
        import json as _json
        _json.dump(data, f, ensure_ascii=False, indent=2, default=json_default)
    count_hint = 0
    if isinstance(data, dict):
        count_hint = len(data)
    elif isinstance(data, list):
        count_hint = len(data)
    print(f"[RTDB][OK] path={path} -> {out_file} (top-level items: {count_hint})")
    return {"path": path, "out_file": out_file, "top_level_items": count_hint}

# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', help='GCP Project ID (ADC 기본값 사용 가능)')
    ap.add_argument('--out-dir', default='dump_all', help='결과 저장 디렉터리')
    ap.add_argument('--collections', nargs='*', help='Firestore: 지정 컬렉션만 내보내기 (기본: 모든 루트 컬렉션)')
    ap.add_argument('--max-depth', type=int, default=10, help='Firestore 서브컬렉션 재귀 최대 깊이')
    ap.add_argument('--rtdb-url', help='Realtime Database URL (https://<db>.firebaseio.com 또는 *.firebasedatabase.app)')
    ap.add_argument('--rtdb-path', default='/', help='Realtime Database export path (기본: /)')
    ap.add_argument('--zip', action='store_true', help='결과를 zip으로도 묶기')
    args = ap.parse_args()

    # Initialize Admin SDK
    opts = {}
    if args.project:
        opts['projectId'] = args.project
    if args.rtdb_url:
        opts['databaseURL'] = args.rtdb_url

    if not firebase_admin._apps:
        if opts:
            firebase_admin.initialize_app(credentials.ApplicationDefault(), opts)
        else:
            firebase_admin.initialize_app(credentials.ApplicationDefault())

    # Firestore client
    db = firestore.Client(project=args.project) if args.project else firestore.Client()

    # Prepare dirs
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = os.path.abspath(args.out_dir)
    out_fs = os.path.join(out_root, "firestore")
    out_rtdb = os.path.join(out_root, "rtdb")
    os.makedirs(out_root, exist_ok=True)

    manifest = {
        "project": args.project,
        "timestamp_utc": ts,
        "firestore": {},
        "rtdb": {},
    }

    # Firestore export
    print("[*] Firestore export start")
    fs_results = fs_export_all(db, out_fs, collections=args.collections, max_depth=args.max_depth)
    manifest["firestore"]["collections"] = fs_results
    print("[*] Firestore export done")

    # RTDB export (optional)
    if args.rtdb_url:
        print("[*] RTDB export start")
        os.makedirs(out_rtdb, exist_ok=True)
        out_rtdb_file = os.path.join(out_rtdb, "rtdb_dump.json")
        rtdb_res = rtdb_export(args.rtdb_url, args.rtdb_path, out_rtdb_file)
        manifest["rtdb"] = {"url": args.rtdb_url, **rtdb_res}
        print("[*] RTDB export done")
    else:
        print("[*] RTDB export skipped (no --rtdb-url)")

    # Write manifest
    manifest_path = os.path.join(out_root, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        import json as _json
        _json.dump(manifest, f, ensure_ascii=False, indent=2, default=json_default)
    print(f"[OK] wrote manifest: {manifest_path}")

    # Optional zip
    if args.zip:
        zip_path = out_root.rstrip("/\\") + ".zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(out_root):
                for name in files:
                    p = os.path.join(root, name)
                    arc = os.path.relpath(p, start=os.path.dirname(out_root))
                    zf.write(p, arcname=arc)
        print(f"[OK] wrote zip: {zip_path}")

    print("[DONE] All exports completed.")

if __name__ == "__main__":
    import zipfile  # used in --zip branch
    main()
