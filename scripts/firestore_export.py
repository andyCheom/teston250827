#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Firestore 데이터 백업 스크립트"""

import os
import sys
import json
import csv
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from google.cloud import firestore
from google.oauth2 import service_account

# Windows 환경에서 UTF-8 출력 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

class FirestoreExporter:
    """Firestore 데이터 내보내기 도구"""
    
    def __init__(self, project_id: str, credentials_path: str = None):
        self.project_id = project_id
        
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.db = firestore.Client(project=project_id, credentials=credentials)
        else:
            # 환경변수나 기본 인증 사용
            self.db = firestore.Client(project=project_id)
    
    def list_collections(self) -> List[str]:
        """모든 컬렉션 이름 가져오기"""
        collections = self.db.collections()
        return [col.id for col in collections]
    
    def export_collection_to_json(self, collection_name: str, output_dir: str = "backup") -> str:
        """컬렉션을 JSON 파일로 내보내기"""
        docs = self.db.collection(collection_name).stream()
        data = []
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['_id'] = doc.id
            doc_data['_collection'] = collection_name
            
            # 타임스탬프 처리
            for key, value in doc_data.items():
                if hasattr(value, 'timestamp'):  # Firestore timestamp
                    doc_data[key] = value.isoformat()
            
            data.append(doc_data)
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(exist_ok=True)
        
        # 파일명에 타임스탬프 포함
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/{collection_name}_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ {collection_name}: {len(data)}개 문서 → {output_file}")
        return output_file
    
    def export_collection_to_csv(self, collection_name: str, output_dir: str = "backup") -> str:
        """컬렉션을 CSV 파일로 내보내기"""
        docs = self.db.collection(collection_name).stream()
        data = []
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['_id'] = doc.id
            doc_data['_collection'] = collection_name
            
            # 중첩된 객체를 문자열로 변환
            for key, value in doc_data.items():
                if isinstance(value, (dict, list)):
                    doc_data[key] = json.dumps(value, ensure_ascii=False, default=str)
                elif hasattr(value, 'timestamp'):
                    doc_data[key] = value.isoformat()
            
            data.append(doc_data)
        
        if not data:
            print(f"⚠️ {collection_name}: 데이터가 없습니다")
            return None
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(exist_ok=True)
        
        # CSV 파일 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/{collection_name}_{timestamp}.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        
        print(f"✅ {collection_name}: {len(data)}개 문서 → {output_file}")
        return output_file
    
    def export_all_collections(self, format: str = "json", output_dir: str = "backup"):
        """모든 컬렉션을 내보내기"""
        collections = self.list_collections()
        print(f"📋 발견된 컬렉션: {collections}")
        
        exported_files = []
        for collection_name in collections:
            try:
                if format.lower() == "json":
                    file_path = self.export_collection_to_json(collection_name, output_dir)
                elif format.lower() == "csv":
                    file_path = self.export_collection_to_csv(collection_name, output_dir)
                else:
                    print(f"❌ 지원하지 않는 형식: {format}")
                    continue
                
                if file_path:
                    exported_files.append(file_path)
                    
            except Exception as e:
                print(f"❌ {collection_name} 내보내기 실패: {e}")
        
        print(f"\n🎉 내보내기 완료: {len(exported_files)}개 파일")
        return exported_files
    
    def query_and_export(self, collection_name: str, field: str, operator: str, value: Any, 
                        output_dir: str = "backup", format: str = "json") -> str:
        """조건에 맞는 데이터만 내보내기"""
        query = self.db.collection(collection_name).where(field, operator, value)
        docs = query.stream()
        
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['_id'] = doc.id
            data.append(doc_data)
        
        if not data:
            print(f"⚠️ 조건에 맞는 데이터가 없습니다: {field} {operator} {value}")
            return None
        
        # 파일 저장
        Path(output_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "json":
            output_file = f"{output_dir}/{collection_name}_filtered_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        else:
            output_file = f"{output_dir}/{collection_name}_filtered_{timestamp}.csv"
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        
        print(f"✅ 필터링된 데이터: {len(data)}개 문서 → {output_file}")
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Firestore 데이터 내보내기 도구')
    parser.add_argument('--project-id', required=True, help='GCP 프로젝트 ID')
    parser.add_argument('--credentials', help='서비스 계정 키 파일 경로')
    parser.add_argument('--collection', help='특정 컬렉션만 내보내기')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='출력 형식')
    parser.add_argument('--output-dir', default='backup', help='출력 디렉토리')
    parser.add_argument('--all', action='store_true', help='모든 컬렉션 내보내기')
    
    # 필터링 옵션
    parser.add_argument('--filter-field', help='필터링할 필드명')
    parser.add_argument('--filter-operator', choices=['==', '!=', '<', '<=', '>', '>=', 'in', 'not-in'], 
                       help='필터링 연산자')
    parser.add_argument('--filter-value', help='필터링 값')
    
    args = parser.parse_args()
    
    # Firestore 내보내기 도구 초기화
    exporter = FirestoreExporter(args.project_id, args.credentials)
    
    try:
        if args.all:
            # 모든 컬렉션 내보내기
            exporter.export_all_collections(args.format, args.output_dir)
        elif args.collection:
            # 특정 컬렉션 내보내기
            if args.filter_field and args.filter_operator and args.filter_value:
                # 필터링 적용
                exporter.query_and_export(
                    args.collection, 
                    args.filter_field, 
                    args.filter_operator, 
                    args.filter_value,
                    args.output_dir,
                    args.format
                )
            else:
                # 전체 컬렉션
                if args.format == 'json':
                    exporter.export_collection_to_json(args.collection, args.output_dir)
                else:
                    exporter.export_collection_to_csv(args.collection, args.output_dir)
        else:
            # 사용 가능한 컬렉션 목록 표시
            collections = exporter.list_collections()
            print("📋 사용 가능한 컬렉션:")
            for col in collections:
                print(f"  • {col}")
            print("\n💡 사용법:")
            print(f"  python {__file__} --project-id {args.project_id} --collection COLLECTION_NAME")
            print(f"  python {__file__} --project-id {args.project_id} --all")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())