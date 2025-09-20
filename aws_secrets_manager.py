"""
AWS Secrets Manager 및 Parameter Store 연동 모듈
민감한 정보를 안전하게 관리하기 위한 모듈
"""

import os
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSSecretsManager:
    """AWS Secrets Manager 및 Parameter Store 관리 클래스"""
    
    def __init__(self, region_name='ap-northeast-2'):
        """AWS Secrets Manager 초기화"""
        self.region_name = region_name
        try:
            self.secrets_client = boto3.client('secretsmanager', region_name=region_name)
            self.ssm_client = boto3.client('ssm', region_name=region_name)
            logger.info("AWS Secrets Manager 클라이언트 초기화 완료")
        except NoCredentialsError:
            logger.error("AWS 자격 증명을 찾을 수 없습니다.")
            self.secrets_client = None
            self.ssm_client = None
        except Exception as e:
            logger.error(f"AWS 클라이언트 초기화 실패: {e}")
            self.secrets_client = None
            self.ssm_client = None
    
    def get_secret(self, secret_name, key=None):
        """Secrets Manager에서 시크릿 값을 가져옵니다."""
        if not self.secrets_client:
            logger.warning("Secrets Manager 클라이언트를 사용할 수 없습니다.")
            return None
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            
            if 'SecretString' in response:
                secret_data = json.loads(response['SecretString'])
                
                if key:
                    return secret_data.get(key)
                else:
                    return secret_data
            else:
                logger.error(f"시크릿 {secret_name}에 SecretString이 없습니다.")
                return None
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DecryptionFailureException':
                logger.error(f"시크릿 {secret_name} 복호화 실패")
            elif error_code == 'InternalServiceErrorException':
                logger.error(f"AWS 내부 서비스 오류")
            elif error_code == 'InvalidParameterException':
                logger.error(f"잘못된 매개변수")
            elif error_code == 'InvalidRequestException':
                logger.error(f"잘못된 요청")
            elif error_code == 'ResourceNotFoundException':
                logger.error(f"시크릿 {secret_name}을 찾을 수 없습니다.")
            else:
                logger.error(f"시크릿 {secret_name} 조회 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"시크릿 {secret_name} 조회 중 예상치 못한 오류: {e}")
            return None
    
    def get_parameter(self, parameter_name, decrypt=False):
        """Parameter Store에서 파라미터 값을 가져옵니다."""
        if not self.ssm_client:
            logger.warning("Parameter Store 클라이언트를 사용할 수 없습니다.")
            return None
        
        try:
            response = self.ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=decrypt
            )
            return response['Parameter']['Value']
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ParameterNotFound':
                logger.error(f"파라미터 {parameter_name}을 찾을 수 없습니다.")
            elif error_code == 'AccessDenied':
                logger.error(f"파라미터 {parameter_name}에 대한 접근 권한이 없습니다.")
            else:
                logger.error(f"파라미터 {parameter_name} 조회 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"파라미터 {parameter_name} 조회 중 예상치 못한 오류: {e}")
            return None
    
    def get_parameters_by_path(self, path, recursive=True, decrypt=False):
        """Parameter Store에서 경로별로 파라미터들을 가져옵니다."""
        if not self.ssm_client:
            logger.warning("Parameter Store 클라이언트를 사용할 수 없습니다.")
            return {}
        
        try:
            paginator = self.ssm_client.get_paginator('get_parameters_by_path')
            page_iterator = paginator.paginate(
                Path=path,
                Recursive=recursive,
                WithDecryption=decrypt
            )
            
            parameters = {}
            for page in page_iterator:
                for param in page['Parameters']:
                    param_name = param['Name'].replace(path, '').lstrip('/')
                    parameters[param_name] = param['Value']
            
            return parameters
            
        except Exception as e:
            logger.error(f"파라미터 경로 {path} 조회 실패: {e}")
            return {}

def load_config_from_aws():
    """AWS Secrets Manager 및 Parameter Store에서 설정을 로드합니다."""
    secrets_manager = AWSSecretsManager()
    
    config = {}
    
    # Secrets Manager에서 민감한 정보 로드
    try:
        # 데이터베이스 연결 정보
        db_secrets = secrets_manager.get_secret('snspmt/database')
        if db_secrets:
            config.update({
                'DATABASE_URL': db_secrets.get('DATABASE_URL'),
                'DB_HOST': db_secrets.get('DB_HOST'),
                'DB_PORT': db_secrets.get('DB_PORT'),
                'DB_NAME': db_secrets.get('DB_NAME'),
                'DB_USER': db_secrets.get('DB_USER'),
                'DB_PASSWORD': db_secrets.get('DB_PASSWORD')
            })
        
        # API 키들
        api_secrets = secrets_manager.get_secret('snspmt/api-keys')
        if api_secrets:
            config.update({
                'SMMPANEL_API_KEY': api_secrets.get('SMMPANEL_API_KEY'),
                'FIREBASE_API_KEY': api_secrets.get('FIREBASE_API_KEY'),
                'FIREBASE_AUTH_DOMAIN': api_secrets.get('FIREBASE_AUTH_DOMAIN'),
                'FIREBASE_PROJECT_ID': api_secrets.get('FIREBASE_PROJECT_ID')
            })
            
    except Exception as e:
        logger.error(f"Secrets Manager에서 설정 로드 실패: {e}")
    
    # Parameter Store에서 일반 설정 로드
    try:
        app_params = secrets_manager.get_parameters_by_path('/snspmt/app/')
        config.update(app_params)
        
        db_params = secrets_manager.get_parameters_by_path('/snspmt/database/')
        config.update(db_params)
        
    except Exception as e:
        logger.error(f"Parameter Store에서 설정 로드 실패: {e}")
    
    # 환경 변수로 fallback
    for key in config:
        if config[key] is None:
            config[key] = os.environ.get(key)
    
    return config

def get_database_url():
    """데이터베이스 URL을 가져옵니다."""
    # 1. 환경 변수에서 직접 가져오기
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url
    
    # 2. AWS Secrets Manager에서 가져오기
    secrets_manager = AWSSecretsManager()
    database_url = secrets_manager.get_secret('snspmt/database', 'DATABASE_URL')
    if database_url:
        return database_url
    
    # 3. 기본값 반환
    return 'postgresql://postgres:Snspmt2024!@snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt'

def get_smmpanel_api_key():
    """SMM Panel API 키를 가져옵니다."""
    # 1. 환경 변수에서 직접 가져오기
    api_key = os.environ.get('SMMPANEL_API_KEY')
    if api_key:
        return api_key
    
    # 2. AWS Secrets Manager에서 가져오기
    secrets_manager = AWSSecretsManager()
    api_key = secrets_manager.get_secret('snspmt/api-keys', 'SMMPANEL_API_KEY')
    if api_key:
        return api_key
    
    # 3. 기본값 반환
    return '5efae48d287931cf9bd80a1bc6fdfa6d'

if __name__ == "__main__":
    # 테스트 코드
    print("AWS Secrets Manager 테스트")
    
    secrets_manager = AWSSecretsManager()
    
    # 데이터베이스 URL 테스트
    db_url = get_database_url()
    print(f"데이터베이스 URL: {db_url[:50]}...")
    
    # API 키 테스트
    api_key = get_smmpanel_api_key()
    print(f"API 키: {api_key[:20]}...")
    
    # 전체 설정 로드 테스트
    config = load_config_from_aws()
    print(f"로드된 설정 키들: {list(config.keys())}")
