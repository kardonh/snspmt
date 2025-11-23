#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
모든 Flask API 엔드포인트에 기본 Swagger 문서화 주석을 자동으로 추가하는 스크립트
"""

import re
import sys

def extract_route_info(line):
    """@app.route 데코레이터에서 경로와 메서드 추출"""
    # @app.route('/api/example', methods=['GET', 'POST'])
    route_match = re.search(r"@app\.route\(['\"]([^'\"]+)['\"]", line)
    if not route_match:
        return None, None
    
    route_path = route_match.group(1)
    
    # methods 추출
    methods_match = re.search(r"methods=\[([^\]]+)\]", line)
    if methods_match:
        methods_str = methods_match.group(1)
        methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
    else:
        methods = ['GET']  # 기본값
    
    return route_path, methods

def get_tag_from_path(path):
    """경로에서 태그 추출"""
    if '/api/admin' in path:
        return 'Admin'
    elif '/api/users' in path or '/api/user' in path:
        return 'Users'
    elif '/api/points' in path:
        return 'Points'
    elif '/api/orders' in path:
        return 'Orders'
    elif '/api/referral' in path:
        return 'Referral'
    elif '/api/blog' in path:
        return 'Blog'
    elif '/api/auth' in path:
        return 'Auth'
    elif '/api/categories' in path or '/api/products' in path or '/api/packages' in path:
        return 'Products'
    elif '/api/health' in path or '/health' in path:
        return 'Health'
    elif '/api/config' in path:
        return 'Config'
    elif '/api/cron' in path:
        return 'Cron'
    elif '/api/smm-panel' in path:
        return 'SMM Panel'
    else:
        return 'API'

def generate_swagger_doc(route_path, methods, function_name, existing_doc=""):
    """기본 Swagger 문서화 주석 생성"""
    
    # 이미 Swagger 주석이 있으면 건너뛰기
    if existing_doc and '---' in existing_doc:
        return None
    
    tag = get_tag_from_path(route_path)
    method = methods[0] if methods else 'GET'
    
    # 경로 파라미터 추출
    path_params = re.findall(r'<([^:>]+):([^>]+)>', route_path)
    query_params = []
    
    # 기본 설명 생성
    summary = function_name.replace('_', ' ').title()
    description = f"{summary} API"
    
    # 파라미터 섹션 생성
    parameters_section = ""
    if path_params:
        parameters_section = "    parameters:\n"
        for param_type, param_name in path_params:
            parameters_section += f"""      - name: {param_name}
        in: path
        type: {param_type if param_type != 'path' else 'string'}
        required: true
        description: {param_name.replace('_', ' ').title()}
        example: "example_{param_name}"
"""
    
    # body 파라미터 (POST, PUT, PATCH)
    if method in ['POST', 'PUT', 'PATCH']:
        if not path_params:
            parameters_section = """    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
"""
        else:
            parameters_section += """      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
"""
    
    # query 파라미터 (GET)
    if method == 'GET' and not path_params:
        parameters_section = """    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
"""
    
    # 응답 섹션
    responses_section = """    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
"""
    
    # Security (Admin, Auth 관련)
    security_section = ""
    if '/admin' in route_path or '/auth' in route_path:
        security_section = """    security:
      - Bearer: []
"""
    
    # 전체 Swagger 주석 생성
    swagger_doc = f"""    \"\"\"{summary}
    ---
    tags:
      - {tag}
    summary: {summary}
    description: "{description}"
{security_section}{parameters_section}{responses_section}    \"\"\" """
    
    return swagger_doc

def process_file(file_path):
    """파일을 읽고 Swagger 주석 추가"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    modified = False
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # @app.route 찾기
        if '@app.route' in line:
            route_path, methods = extract_route_info(line)
            
            if route_path:
                # 다음 몇 줄을 확인하여 함수 정의 찾기
                j = i + 1
                function_def = None
                function_name = None
                
                while j < len(lines) and j < i + 10:
                    if lines[j].strip().startswith('def '):
                        function_def = lines[j]
                        function_name_match = re.search(r'def\s+(\w+)', function_def)
                        if function_name_match:
                            function_name = function_name_match.group(1)
                        break
                    j += 1
                
                if function_name:
                    # 함수 정의까지 이동
                    while i + 1 < len(lines) and not lines[i + 1].strip().startswith('def '):
                        i += 1
                        new_lines.append(lines[i])
                    
                    if i + 1 < len(lines):
                        i += 1
                        func_line = lines[i]
                        new_lines.append(func_line)
                        
                        # 다음 줄이 docstring인지 확인
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]
                            
                            # 기존 docstring 확인
                            existing_doc = ""
                            doc_start = i + 1
                            
                            if '"""' in next_line or "'''" in next_line:
                                # 기존 docstring 읽기
                                quote_type = '"""' if '"""' in next_line else "'''"
                                doc_lines = [next_line]
                                doc_end = i + 1
                                
                                # docstring이 한 줄에 있는지 확인
                                if next_line.count(quote_type) == 2:
                                    existing_doc = next_line
                                else:
                                    # 여러 줄 docstring
                                    k = i + 2
                                    while k < len(lines):
                                        doc_lines.append(lines[k])
                                        if quote_type in lines[k]:
                                            doc_end = k
                                            break
                                        k += 1
                                    existing_doc = ''.join(doc_lines)
                            
                            # Swagger 주석이 없으면 추가
                            if '---' not in existing_doc:
                                swagger_doc = generate_swagger_doc(
                                    route_path, methods, function_name, existing_doc
                                )
                                
                                if swagger_doc:
                                    # 기존 docstring이 있으면 유지하고 Swagger 추가
                                    if existing_doc and existing_doc.strip():
                                        # 기존 docstring의 첫 줄만 유지
                                        first_line = existing_doc.split('\n')[0]
                                        if '"""' in first_line or "'''" in first_line:
                                            # 기존 docstring 제거하고 새로 작성
                                            quote_type = '"""' if '"""' in first_line else "'''"
                                            # 기존 docstring 건너뛰기
                                            if quote_type in next_line:
                                                if next_line.count(quote_type) == 2:
                                                    # 한 줄 docstring
                                                    i += 1
                                                    new_lines.pop()  # 마지막에 추가한 함수 정의 라인 제거
                                                    new_lines.append(func_line)
                                                    # 새로운 docstring 추가
                                                    new_lines.append(swagger_doc + '\n')
                                                    modified = True
                                                    continue
                                                else:
                                                    # 여러 줄 docstring 건너뛰기
                                                    k = i + 2
                                                    while k < len(lines):
                                                        if quote_type in lines[k]:
                                                            i = k
                                                            break
                                                        k += 1
                                                    # 새로운 docstring 추가
                                                    new_lines.append(swagger_doc + '\n')
                                                    modified = True
                                                    continue
                                    else:
                                        # docstring이 없으면 추가
                                        new_lines.append(swagger_doc + '\n')
                                        modified = True
        
        i += 1
    
    if modified:
        # 백업 생성
        backup_path = file_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✅ 백업 파일 생성: {backup_path}")
        
        # 새 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✅ Swagger 주석 추가 완료: {file_path}")
        return True
    else:
        print("ℹ️ 추가할 Swagger 주석이 없습니다.")
        return False

if __name__ == '__main__':
    file_path = 'backend.py'
    print(f"🔍 {file_path} 파일 처리 중...")
    process_file(file_path)
    print("✅ 완료!")

