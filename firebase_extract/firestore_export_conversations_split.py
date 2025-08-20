# -*- coding: utf-8 -*-
"""
Firestore 'conversations' 컬렉션을 문서별 폴더(conversations/<session_id>/)로 저장.

- 기본: document.json 하나에 서브컬렉션까지 중첩 저장
- --split-subcollections: 서브컬렉션을 별도 파일(<subcol>.json)로 분리 저장

Usage:
  pip install firebase-admin google-cloud-firestore
  gcloud auth application-default login
  gcloud config set project <PROJECT_ID>

  python firestore_export_conversations_split.py \
    --project <PROJECT_ID> \
    --out-dir dump_sessions \
    --collection conversations \
    --split-subcollections
"""
import os, json, argparse, base64, decimal
import datetime as _dt
from typing import Dict, Any
import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore

# ---------- JSON serializer for Firestore special types ----------
def json_default(o):
    if isinstance(o, _dt.datetime):
        if o.tzinfo is None:
            return o.isoformat()
        return o.astimezone(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(o, (_dt.date, _dt.time)):
        return o.isoformat()
    if isinstance(o, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(o)).decode("ascii")
    if isinstance(o, decimal.Decimal):
        return float(o)
    if hasattr(o, "path") and hasattr(o, "id") and hasattr(o, "get"):
        return {"__type__":"document_ref", "path": o.path}
    if hasattr(o, "latitude") and hasattr(o, "longitude"):
        try:
            return {"__type__":"geo_point", "lat": float(o.latitude), "lng": float(o.longitude)}
        except Exception:
            return {"__type__":"geo_point", "lat": o.latitude, "lng": o.longitude}
    if isinstance(o, (set, frozenset)):
        return list(o)
    return str(o)

def serialize_document(doc_snap) -> Dict[str, Any]:
    return {"id": doc_snap.id, "path": doc_snap.reference.path, "fields": doc_snap.to_dict() or {}}

def export_subcollections_to_dict(doc_ref, max_depth=5, depth=0):
    if depth >= max_depth:
        return {}
    result = {}
    for subcol in doc_ref.collections():
        docs = []
        for subdoc in subcol.stream():
            node = serialize_document(subdoc)
            node["subcollections"] = export_subcollections_to_dict(subdoc.reference, max_depth, depth+1)
            docs.append(node)
        result[subcol.id] = docs
    return result

def export_collection_per_doc_folders(db, out_root: str, collection_name: str, split_subcollections: bool, max_depth:int):
    os.makedirs(out_root, exist_ok=True)
    coll = db.collection(collection_name)
    count = 0
    for doc in coll.stream():
        count += 1
        folder = os.path.join(out_root, collection_name, doc.id)
        os.makedirs(folder, exist_ok=True)

        node = serialize_document(doc)
        if split_subcollections:
            # 1) 본문만 저장
            out_file = os.path.join(folder, "document.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(node, f, ensure_ascii=False, indent=2, default=json_default)
            # 2) 서브컬렉션을 각 파일로
            sub = export_subcollections_to_dict(doc.reference, max_depth=max_depth, depth=0)
            for subname, items in sub.items():
                sub_path = os.path.join(folder, f"{subname}.json")
                with open(sub_path, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2, default=json_default)
        else:
            # 서브컬렉션을 중첩해서 하나의 파일로
            node["subcollections"] = export_subcollections_to_dict(doc.reference, max_depth=max_depth, depth=0)
            out_file = os.path.join(folder, "document.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(node, f, ensure_ascii=False, indent=2, default=json_default)

        print(f"[OK] wrote {out_file}")
    print(f"[DONE] exported {count} docs from '{collection_name}' into '{out_root}/{collection_name}/<docId>/'")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', help='GCP Project ID (ADC 기본값 사용 가능)')
    ap.add_argument('--out-dir', required=True, help='결과 저장 루트 디렉터리')
    ap.add_argument('--collection', default='conversations', help='루트 컬렉션 이름')
    ap.add_argument('--split-subcollections', action='store_true', help='하위 컬렉션을 별도 JSON으로 분리 저장')
    ap.add_argument('--max-depth', type=int, default=5, help='하위 컬렉션 재귀 최대 깊이')
    args = ap.parse_args()

    if not firebase_admin._apps:
        if args.project:
            firebase_admin.initialize_app(credentials.ApplicationDefault(), {'projectId': args.project})
        else:
            firebase_admin.initialize_app(credentials.ApplicationDefault())
    db = firestore.Client(project=args.project) if args.project else firestore.Client()

    out_root = os.path.abspath(args.out_dir)
    export_collection_per_doc_folders(db, out_root, args.collection, args.split_subcollections, args.max_depth)

if __name__ == "__main__":
    main()
