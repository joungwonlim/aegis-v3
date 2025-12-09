# AEGIS v3.1 백엔드 최적화 가이드

## 1. 데이터베이스 쿼리 최적화

### 1.1 N+1 문제 해결
**문제 상황**: 연관된 객체를 조회할 때 메인 쿼리 1번에 대해 N개의 추가 쿼리가 발생하는 문제
```python
# 문제 코드
users = User.objects.all()
for user in users:
    print(user.profile.bio)  # 각 user마다 별도 쿼리 실행
```

**해결 방법**: `select_related` 또는 `prefetch_related` 사용
```python
# 개선된 코드 (Django ORM 예시)
# 1:1 관계 - select_related
users = User.objects.select_related('profile').all()

# 1:N 관계 - prefetch_related
users = User.objects.prefetch_related('posts').all()

# 복합 관계
users = User.objects.prefetch_related(
    Prefetch('posts', queryset=Post.objects.select_related('category'))
).all()
```

**성능 개선 수치**:
- 쿼리 수: N+1 → 1~2개로 감소
- 응답 시간: 60-95% 감소 (N에 따라 다름)

**적용 시 주의사항**:
- `select_related`: JOIN 사용, 1:1 또는 N:1 관계에 적합
- `prefetch_related`: 별도 쿼리 실행 후 메모리에서 조인, M:N 관계에 적합
- 너무 많은 관계를 한번에 프리패치하면 메모리 부하 발생

### 1.2 인덱스 전략
**문제 상황**: 풀 테이블 스캔으로 인한 느린 쿼리 실행
```sql
-- 인덱스 없이 WHERE 절 사용
SELECT * FROM orders WHERE user_id = 123 AND status = 'completed';
```

**해결 방법**: 적절한 복합 인덱스 생성
```python
# Django 모델 예시
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            # 복합 인덱스: 자주 함께 사용되는 조건
            models.Index(fields=['user', 'status', '-created_at']),
            
            # 단일 컬럼 인덱스
            models.Index(fields=['created_at']),
            
            # 부분 인덱스: 특정 조건의 데이터만 인덱싱
            models.Index(
                fields=['status'],
                name='idx_active_orders',
                condition=models.Q(status='active')
            )
        ]
```

**성능 개선 수치**:
- 조회 속도: 10-1000배 향상
- CPU 사용량: 40-70% 감소

**적용 시 주의사항**:
- 인덱스는 쓰기 성능을 저하시킴 (인덱스 유지 비용)
- 카디널리티가 높은 컬럼에 인덱스 적용이 효과적
- 복합 인덱스의 컬럼 순서가 중요 (왼쪽 우선 정렬)

### 1.3 쿼리 캐싱 (Redis)
**문제 상황**: 빈번하게 동일한 쿼리 반복 실행
```python
# 캐싱 없이 매번 DB 조회
def get_popular_products():
    return Product.objects.filter(
        rating__gte=4.5,
        stock_count__gt=0
    ).order_by('-sales_count')[:10]
```

**해결 방법**: Redis를 이용한 결과 캐싱
```python
import redis
from django.core.cache import cache
import pickle
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_query(ttl=300, key_prefix='query'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 캐시에서 조회
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return pickle.loads(cached_result)
            
            # 캐시 미스시 DB 조회
            result = func(*args, **kwargs)
            
            # 결과 캐싱
            redis_client.setex(
                cache_key,
                ttl,
                pickle.dumps(result)
            )
            return result
        return wrapper
    return decorator

# 사용 예시
@cache_query(ttl=600, key_prefix='products')
def get_popular_products():
    return list(Product.objects.filter(
        rating__gte=4.5,
        stock_count__gt=0
    ).order_by('-sales_count')[:10])
```

**성능 개선 수치**:
- 응답 시간: 0.5ms (Redis) vs 50ms (DB)
- DB 부하: 80-95% 감소
- 처리량: 10-100배 증가

**적용 시 주의사항**:
- 데이터 정합성이 중요한 경우 캐싱 전략 재검토 필요
- TTL(Time To Live) 적절히 설정
- 캐시 스탬피드 문제 방지를 위한 랜덤 TTL 추가 고려

### 1.4 Batch 처리
**문제 상황**: 대량 데이터 처리 시 한번에 많은 쿼리 실행
```python
# 비효율적인 단일 처리
for item in items:
    Item.objects.create(**item)
```

**해결 방법**: bulk_create, batch_size 활용
```python
# bulk_create를 이용한 배치 처리
def create_items_batch(items, batch_size=1000):
    item_instances = [Item(**data) for data in items]
    
    # 한번에 여러 레코드 삽입
    Item.objects.bulk_create(item_instances, batch_size=batch_size)

# iterator()를 이용한 대량 데이터 조회
def process_large_queryset():
    # 메모리 효율적인 조회
    items = Item.objects.filter(status='active').iterator(chunk_size=2000)
    
    for item in items:
        # 대량 데이터 처리
        process_item(item)

# update도 배치 처리
def update_items_batch(item_ids, updates):
    Item.objects.filter(id__in=item_ids).update(**updates)
```

**성능 개선 수치**:
- 삽입 속도: 10-100배 향상
- 메모리 사용량: 60-80% 감소
- 처리 시간: 70-90% 단축

**적용 시 주의사항**:
- bulk_create는 모델의 save() 메서드와 신호(signals)를 호출하지 않음
- 너무 큰 batch_size는 메모리 부하 발생 가능
- 트랜잭션 관리 필요 (atomic 블록 활용)

## 2. API 응답 최적화

### 2.1 페이지네이션
**문제 상황**: 모든 데이터를 한번에 반환하여 응답 크기 과대
```python
# 모든 데이터 반환 (비효율적)
@api_view(['GET'])
def get_all_items(request):
    items = Item.objects.all()
    serializer = ItemSerializer(items, many=True)
    return Response(serializer.data)
```

**해결 방법**: Cursor-based 또는 Offset-based 페이지네이션
```python
# Django REST Framework 페이지네이션
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response

class OptimizedPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

class CursorBasedPagination(CursorPagination):
    page_size = 50
    ordering = '-created_at'  # 커서 기반 정렬 필수

# 뷰에서 적용
class ItemListView(APIView):
    pagination_class = OptimizedPagination
    
    def get(self, request):
        queryset = Item.objects.all()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = ItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ItemSerializer(queryset, many=True)
        return Response(serializer.data)
```

**성능 개선 수치**:
- 응답 크기: 95% 감소 (10만개 → 50개)
- 응답 시간: 80-95% 단축
- 메모리 사용량: 90% 이상 감소

**적용 시 주의사항**:
- 커서 기반 페이지네이션은 정렬 조건 필수
- 페이지 번호 기반은 대량 데이터에서 성능 저하 가능
- 클라이언트 요구사항에 맞는 방식 선택

### 2.2 필드 선택 (GraphQL 스타일)
**문제 상황**: 불필요한 필드까지 모두 반환
```python
# 모든 필드 반환
serializer = UserSerializer(user, many=True)
# 클라이언트는 name 필드만 필요함
```

**해결 방법**: 필드 선택적 반환
```python
# 동적 필드 선택
class DynamicFieldsSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        
        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

# 뷰에서 필드 지정
class UserDetailView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        
        # 쿼리 파라미터에서 필드 추출
        fields = request.query_params.get('fields', '').split(',')
        
        serializer = DynamicFieldsSerializer(
            user, 
            fields=fields if fields else None
        )
        return Response(serializer.data)

# 사용 예시: GET /api/users/1?fields=id,name,email
```

**성능 개선 수치**:
- 응답 크기: 30-70% 감소 (필드 수에 따라)
- 직렬화 시간: 20-50% 단축
- 네트워크 대역폭: 상응 감소

**적용 시 주의사항**:
- 필드 제한이 데이터 일관성에 영향 없도록 설계
- 필드 종속성 고려 (예: address 필드가 필요하면 user 필요)
- 클라이언트 교육 필요

### 2.3 Gzip 압축
**문제 상황**: 대용량 응답으로 인한 네트워크 병목
```python
# 압축 없이 JSON 응답
@api_view(['GET'])
def get_large_data(request):
    data = generate_large_dataset()  # 5MB 데이터
    return Response(data)
```

**해결 방법**: 미들웨어를 통한 자동 압축
```python
# settings.py 설정
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    # ...
]

# Nginx에서 압축 (권장, 더 효율적)
"""
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss 
           application/atom+xml image/svg+xml;
"""

# Python에서 수동 압축
import gzip
import json
from io import BytesIO

def gzip_compressed_response(data):
    json_str = json.dumps(data)
    
    # Gzip 압축
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(json_str.encode('utf-8'))
    
    compressed.seek(0)
    
    response = HttpResponse(compressed, content_type='application/json')
    response['Content-Encoding'] = 'gzip'
    response['Content-Length'] = len(compressed.getvalue())
    return response
```

**성능 개선 수치**:
- 네트워크 전송량: 70-90% 감소 (텍스트 기반 데이터)
- 로딩 시간: 50-80% 단축 (느린 네트워크에서 효과적)
- 서버 대역폭: 상응 감소

**적용 시 주의사항**:
- 이미지, 비디오 등 이미 압축된 파일은 효과 미미
- CPU 사용량 약간 증가 (하드웨어 가속 활용 고려)
- 클라이언트 지원 확인 (모던 브라우저는 모두 지원)

### 2.4 ETag 캐싱
**문제 상황**: 변경되지 않은 데이터에 대한 반복 요청
```python
# 캐싱 없이 항상 전체 응답 생성
@api_view(['GET'])
def get_user_data(request, user_id):
    user = get_object_or_404(User, id=user_id)
    data = {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'updated_at': user.updated_at.isoformat()
    }
    return Response(data)
```

**해결 방법**: ETag를 이용한 조건부 요청
```python
import hashlib
import json

def generate_etag(data):
    """데이터 기반 ETag 생성"""
    content = json.dumps(data, sort_keys=True).encode('utf-8')
    return hashlib.md5(content).hexdigest()

@api_view(['GET'])
def get_user_data(request, user_id):
    user = get_object_or_404(User, id=user_id)
    data = {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'updated_at': user.updated_at.isoformat()
    }
    
    # ETag 생성
    etag = generate_etag(data)
    
    # 클라이언트 ETag 확인
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match == etag:
        # 데이터 변경 없음 - 304 응답
        return Response(status=304)
    
    # 변경되었거나 첫 요청
    response = Response(data)
    response['ETag'] = etag
    response['Cache-Control'] = 'public, max-age=300'  # 5분 캐시
    
    return response

# Django의 ConditionalGetMiddleware 사용
MIDDLEWARE = [
    'django.middleware.http.ConditionalGetMiddleware',
    # ...
]
```

**성능 개선 수치**:
- 불필요한 전송: 60-80% 감소 (변경 없는 경우)
- 서버 부하: 40-70% 감소
- 응답 시간: 1-10ms (304) vs 50-200ms (전체 응답)

**적용 시 주의사항**:
- 동적 콘텐츠에는 적합하지 않음
- ETag 생성 비용이 높을 경우 간소화된 버전 사용
- Last-Modified 헤더와 함께 사용 가능

## 3. 비동기 처리

### 3.1 Celery 작업 큐
**문제 상황**: 장시간 실행 작업이 API 응답 지연
```python
# 동기적으로 장시간 작업 실행
@api_view(['POST'])
def process_video(request):
    video_file = request.FILES['video']
    
    # 5분 이상 소요되는 처리
    result = video_processor.process(video_file)  # 블로킹
    
    return Response({'result': result})  # 사용자는 5분 대기
```

**해결 방법**: Celery를 이용한 비동기 작업 처리
```python
# tasks.py
from celery import Celery
from django.core.mail import send_mail

app = Celery('aegis', broker='redis://localhost:6379/0')

@app.task(bind=True, max_retries=3)
def process_video_task(self, video_path, user_email):
    try:
        # 장시간 작업
        result = video_processor.process(video_path)
        
        # 작업 완료 알림
        send_mail(
            'Video Processing Complete',
            f'Your video processing is complete. Result: {result}',
            'noreply@aegis.com',
            [user_email]
        )
        return result
    except Exception as exc:
        # 재시도
        self.retry(exc=exc, countdown=60)

# views.py
@api_view(['POST'])
def process_video(request):
    video_file = request.FILES['video']
    
    # 파일 저장
    video_path = save_uploaded_file(video_file)
    
    # 비동기 작업 큐에 추가
    task = process_video_task.delay(
        video_path=video_path,
        user_email=request.user.email
    )
    
    # 즉시 응답 (작업 ID 반환)
    return Response({
        'task_id': task.id,
        'status': 'processing',
        'check_status': f'/api/tasks/{task.id}/status/'
    })

# 작업 상태 확인 엔드포인트
@api_view(['GET'])
def check_task_status(request, task_id):
    task_result = AsyncResult(task_id)
    
    return Response({
        'task_id': task_id,
        'status': task_result.status,
        'result': task_result.result if task_result.ready() else None
    })
```

**성능 개선 수치**:
- API 응답 시간: 5분 → 100ms 미만
- 시스템 확장성: 작업자 추가로 수평 확장 가능
- 장애 내성: 재시도 메커니즘으로 신뢰성 향상

**적용 시 주의사항**:
- 작업 결과 저장소 필요 (Redis, DB 등)
- 작업 멱등성(idempotent) 보장 필요
- 작업 상태 모니터링 시스템 구축 권장

### 3.2 asyncio 활용
**문제 상황**: I/O 바운드 작업에서의 불필요한 대기
```python
# 동기 I/O 작업
def fetch_multiple_urls(urls):
    results = []
    for url in urls:
        # 각 요청이 완료될 때까지 대기
        response = requests.get(url)  # 블로킹
        results.append(response.text)
    return results
```

**해결 방법**: asyncio를 이용한 비동기 I/O
```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# 순수 I/O 작업: aiohttp 사용
async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_multiple_urls_async(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# 동기 뷰에서 비동기 함수 호출
def sync_view(request):
    urls = ['http://api1.com', 'http://api2.com', 'http://api3.com']
    
    # 이벤트 루프 실행
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(fetch_multiple_urls_async(urls))
    loop.close()
    
    return Response({'results': results})

# CPU 바운드 작업: 스레드 풀 사용
def cpu_intensive_task(data):
    # CPU 집약적 작업
    return process_data(data)

async def process_batch_async(data_list):
    loop = asyncio.get_event_loop()
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = [
            loop.run_in_executor(executor, cpu_intensive_task, data)
            for data in data_list
        ]
        return await asyncio.gather(*tasks)
```

**성능 개선 수치**:
- I/O 작업 시간: N초 → 1초 미만 (병렬 처리)
- 시스템 자원 활용도: CPU 20% → 70% 이상
- 동시 처리량: 10배 이상 향상

**적용 시 주의사항**:
- asyncio는 I/O 바운드 작업에 효과적
- CPU 바운드 작업은 스레드/프로세스 풀과 함께 사용
- Django의 경우 Django Channels와 통합 고려

### 3.3 백그라운드 작업 스케줄링
**문제 상황**: 주기적 작업이 메인 애플리케이션 성능에 영향
```python
# 메인 프로세스에서 직접 스케줄링 (비효율적)
import time
import threading

def periodic_task():
    while True:
        cleanup_expired_data()  # 정리 작업
        time.sleep(3600)  # 1시간 대기

# 메인 스레드에서 실행 (문제 발생)
thread = threading.Thread(target=periodic_task)
thread.start()
```

**해결 방법**: Celery Beat를 이용한 스케줄링
```python
# celery.py
from celery import Celery
from celery.schedules import crontab

app = Celery('aegis')

# 주기적 작업 설정
app.conf.beat_schedule = {
    'cleanup-expired-data-every-hour': {
        'task': 'tasks.cleanup_expired_data',
        'schedule': crontab(minute=0, hour='*/1'),  # 매시간
    },
    'generate-daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': crontab(minute=0, hour=0),  # 매일 자정
    },
    'sync-with-external-api': {
        'task': 'tasks.sync_external_data',
        'schedule': 300.0,  # 5분마다
    },
}

# tasks.py
@app.task
def cleanup_expired_data():
    """만료된 데이터 정리"""
    from django.utils import timezone
    from datetime import timedelta
    
    expiration_date = timezone.now() - timedelta(days=30)
    
    # 30일 지난 데이터 삭제
    ExpiredData.objects.filter(
        created_at__lt=expiration_date
    ).delete()
    
    return {'deleted_count': count}

@app.task
def sync_external_data():
    """외부 API 동기화"""
    external_data = fetch_from_external_api()
    
    for item in external_data:
        ExternalData.objects.update_or_create(
            external_id=item['id'],
            defaults={'data': item['data']}
        )
    
    return {'synced_items': len(external_data)}

# Beat 실행 명령어
# celery -A aegis beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**성능 개선 수치**:
- 메인 앱 영향도: 100% → 0% (완전 분리)
- 작업 정확성: 시간 기반 정확한 실행
- 모니터링: 중앙화된 작업 관리

**적용 시 주의사항**:
- 분산 환경에서 중복 실행 방지 필요
- 작업 실패 시 알림 시스템 구축
- 스케줄 동적 변경 필요시 DatabaseScheduler 사용

## 4. 메모리 관리

### 4.1 커넥션 풀링
**문제 상황**: 데이터베이스 커넥션 생성/종료 오버헤드
```python
# 매 요청마다 새로운 커넥션 생성
def process_request():
    connection = create_db_connection()  # 비용 큰 작업
    result = connection.execute_query()
    connection.close()  # 커넥션 종료
    return result
```

**해결 방법**: 커넥션 풀 구현
```python
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# PostgreSQL 커넥션 풀
postgresql_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,  # 최대 커넥션 수
    host='localhost',
    database='aegis',
    user='user',
    password='password'
)

@contextmanager
def get_db_connection():
    """커넥션 풀에서 커넥션 가져오기"""
    connection = postgresql_pool.getconn()
    try:
        yield connection
    finally:
        postgresql_pool.putconn(connection)

# 사용 예시
def execute_query(query, params=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

# Django에서의 커넥션 풀 (django-db-connections-pool)
"""
DATABASES = {
    'default': {
        'ENGINE': 'db_pool.postgresql',
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 20,
            'RECYCLE': 3600,  # 1시간 후 커넥션 재생성
        }
    }
}
"""

# Redis 커넥션 풀
import redis

redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
    decode_responses=True
)

redis_client = redis.Redis(connection_pool=redis_pool)
```

**성능 개선 수치**:
- 커넥션 생성 시간: 50-100ms → 1-5ms
- 동시 처리량: 2-5배 향상
- 데이터베이스 부하: 30-50% 감소

**적용 시 주의사항**:
- 풀 크기 조정 필요 (너무 크면 리소스 낭비, 작으면 병목)
- 연결 누수 방지를 위한 적절한 반환 메커니즘
- 장시간 idle 커넥션 재생성 필요

### 4.2 객체 재사용
**문제 상황**: 빈번한 객체 생성/삭제로 인한 GC 부하
```python
# 매번 새로운 객체 생성
def process_items(items):
    results = []
    for item in items:
        # 매 루프마다 새로운 프로세서 생성
        processor = ItemProcessor(item)
        result = processor.process()
        results.append(result)
        # processor는 삭제되고 GC 대상이 됨
    return results
```

**해결 방법**: 객체 풀링과 재사용
```python
from queue import Queue
import threading

class ConnectionPool:
    """데이터베이스 연결 풀"""
    def __init__(self, size, create_connection):
        self.pool = Queue(maxsize=size)
        self.create_connection = create_connection
        self.lock = threading.Lock()
        
        # 초기 연결 생성
        for _ in range(size):
            self.pool.put(create_connection())
    
    def get_connection(self):
        """풀에서 연결 가져오기"""
        try:
            return self.pool.get(block=True, timeout=5)
        except Queue.Empty:
            # 풀에 연결이 없으면 새로 생성 (maxsize 제한 내)
            with self.lock:
                return self.create_connection()
    
    def return_connection(self, connection):
        """연결 반환"""
        if self.pool.full():
            connection.close()  # 풀이 가득 차면 연결 종료
        else:
            self.pool.put(connection)

# 객체 재사용 예시
class ParserPool:
    """파서 객체 풀"""
    _parsers = Queue()
    _max_size = 10
    
    @classmethod
    def get_parser(cls):
        """파서 객체 가져오기"""
        try:
            return cls._parsers.get_nowait()
        except Queue.Empty:
            return DataParser()  # 새로 생성
    
    @classmethod
    def return_parser(cls, parser):
        """파서 객체 반환"""
        parser.reset()  # 상태 초기화
        if cls._parsers.qsize() < cls._max_size:
            cls._parsers.put(parser)
        # 풀이 가득 차면 파서는 GC에 의해 정리됨

# 사용 예시
def process_data_batch(data_list):
    for data in data_list:
        parser = ParserPool.get_parser()
        try:
            result = parser.parse(data)
            yield result
        finally:
            ParserPool.return_parser(parser)
```

**성능 개선 수치**:
- 객체 생성 오버헤드: 80-95% 감소
- GC 부하: 60-80% 감소
- 메모리 사용 패턴: 안정화

**적용 시 주의사항**:
- 상태가 있는 객체는 재사용 전 초기화 필요
- 스레드 안전성 고려
- 풀 크기 모니터링 및 동적 조정 고려

### 4.3 메모리 누수 방지
**문제 상황**: 순환 참조, 캐시 누수 등으로 인한 메모리 증가
```python
# 순환 참조 예시
class Node:
    def __init__(self, value):
        self.value = value
        self.children = []
    
    def add_child(self, child):
        self.children.append(child)
        child.parent = self  # 순환 참조 생성

# 캐시 누수 예시
cache = {}
def get_data(key):
    if key not in cache:
        cache[key] = expensive_operation(key)
    return cache[key]  # 영구적으로 캐시에 저장
```

**해결 방법**: 적절한 메모리 관리 기법 적용
```python
import weakref
import gc
from functools import lru_cache

# 1. 순환 참조 방지: weakref 사용
class Node:
    def __init__(self, value):
        self.value = value
        self.children = []
        self._parent = None
    
    @property
    def parent(self):
        return self._parent() if self._parent else None
    
    @parent.setter
    def parent(self, node):
        self._parent = weakref.ref(node)  # 약한 참조

# 2. 제한된 LRU 캐시
from functools import lru_cache

@lru_cache(maxsize=1024)
def get_data_cached(key):
    return expensive_operation(key)

# 3. 수동 캐시 관리
class ManagedCache:
    def __init__(self, max_size=1000, ttl=3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.access_times = {}
    
    def get(self, key):
        if key in self.cache:
            # TTL 체크
            if time.time() - self.access_times[key] > self.ttl:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key, value):
        # 최대 크기 체크
        if len(self.cache) >= self.max_size:
            # LRU 정책으로 제거
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = value
        self.access_times[key] = time.time()

# 4. 메모리 프로파일링
import tracemalloc
import linecache

def analyze_memory_leaks():
    """메모리 누수 분석"""
    tracemalloc.start()
    
    # 테스트 코드 실행
    run_memory_intensive_operation()
    
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("[ Top 10 memory usage ]")
    for stat in top_stats[:10]:
        frame = stat.traceback[0]
        print(f"{frame.filename}:{frame.lineno}: {stat.size/1024:.1f} KiB")
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print(f'    {line}')
    
    tracemalloc.stop()

# 5. 정기적 GC 실행
import gc

def optimize_memory_usage():
    """메모리 사용 최적화"""
    # 수집 가능한 객체 강제 수집
    collected = gc.collect()
    print(f"GC collected {collected} objects")
    
    # 순환 참조 디버깅
    if gc.garbage:
        print(f"Uncollectable objects: {len(gc.garbage)}")
        for obj in gc.garbage:
            print(f"  {type(obj)}: {obj}")
```

**성능 개선 수치**:
- 메모리 사용량: 30-70% 감소 (누수 제거 시)
- GC 오버헤드: 40-60% 감소
- 애플리케이션 안정성: 향상

**적용 시 주의사항**:
- weakref 사용 시 객체가 삭제될 수 있음
- 너무 빈번한 GC는 성능 저하 초래
- 프로덕션에서 메모리 프로파일링은 주의해서 사용

## 5. 모니터링 및 프로파일링

### 5.1 APM 도구 (New Relic, Datadog)
**문제 상황**: 성능 문제 원인 파악 어려움
```python
# 모니터링 없이 문제 진단
try:
    result = complex_operation()
except Exception as e:
    print(f"Error: {e}")  # 제한된 정보
```

**해결 방법**: APM 도구 통합
```python
# New Relic 통합 예시
# newrelic.ini 설정
"""
[newrelic]
license_key = YOUR_LICENSE_KEY
app_name = AEGIS Production
monitor_mode = true
"""

# 코드 수준 모니터링
import newrelic.agent

@newrelic.agent.background_task()
def process_order(order_id):
    """주문 처리 - New Relic에서 모니터링"""
    with newrelic.agent.FunctionTrace('validate_order'):
        validate_order(order_id)
    
    with newrelic.agent.FunctionTrace('charge_payment'):
        charge_payment(order_id)
    
    with newrelic.agent.FunctionTrace('send_confirmation'):
        send_confirmation(order_id)

# 사용자 정의 메트릭
def track_custom_metrics():
    newrelic.agent.record_custom_metric('Custom/Orders/Processed', 1)
    newrelic.agent.record_custom_metric('Custom/Orders/Value', order_value)

# Datadog 통합
from ddtrace import tracer
import ddtrace.contrib.django

# settings.py
MIDDLEWARE = [
    'ddtrace.contrib.django.TraceMiddleware',
    # ...
]

# 데코레이터를 이용한 추적
@tracer.wrap(service='aegis', resource='video_processing')
def process_video(video_path):
    # 비디오 처리 로직
    pass

# 커스텀 스팬
with tracer.trace('complex.calculation', service='aegis-calculator') as span:
    span.set_tag('input_size', len(data))
    result = perform_complex_calculation(data)
    span.set_tag('result', result)

# Prometheus + Grafana 메트릭 수집
from prometheus_client import Counter, Histogram, start_http_server
import time

# 메트릭 정의
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests')
REQUEST_LATENCY = Histogram('http_request_latency_seconds', 'HTTP Request Latency')

# 데코레이터로 메트릭 수집
def track_metrics(view_func):
    def wrapper(request, *args, **kwargs):
        REQUEST_COUNT.inc()
        
        start_time = time.time()
        response = view_func(request, *args, **kwargs)
        latency = time.time() - start_time
        
        REQUEST_LATENCY.observe(latency)
        return response
    return wrapper

# 메트릭 서버 시작
start_http_server(8000)
```

**성능 개선 수치**:
- 문제 진단 시간: 시간/일 → 분 단위
- MTTR(평균 복구 시간): 80% 단축
- 성능 가시성: 0% → 100% 모니터링

**적용 시 주의사항**:
- APM 도구 오버헤드 모니터링 (보통 1-5%)
- 민감한 데이터 수집 시 개인정보 보호 고려
- 비용 관리 (트래픽에 따른 과금)

### 5.2 로그 분석
**문제 상황**: 분산된 로그로 인한 문제 추적 어려움
```python
# 기본 로깅
import logging

logging.basicConfig(level=logging.INFO)
logging.info(f"Processing order {order_id}")  # 구조화되지 않은 로그
```

**해결 방법**: 구조화된 로깅과 중앙 집중화
```python
import logging
import json
import structlog
from pythonjsonlogger import jsonlogger

# 구조화된 로깅 설정
def setup_structured_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()  # JSON 출력
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()

# 로거 사용
logger = setup_structured_logging()

# 구조화된 로그 기록
def process_order(order_id, user_id):
    logger.info("order_processing_started", 
                order_id=order_id, 
                user_id=user_id,
                timestamp=time.time())
    
    try:
        result = execute_order(order_id)
        logger.info("order_processing_completed",
                    order_id=order_id,
                    processing_time=result.time_taken,
                    status="success")
        return result
    except Exception as e:
        logger.error("order_processing_failed",
                     order_id=order_id,
                     error_type=type(e).__name__,
                     error_message=str(e),
                     status="failed")
        raise

# 로그 컨텍스트 관리 (요청 ID 포함)
from contextvars import ContextVar
import uuid

request_id = ContextVar('request_id', default=None)

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get() or str(uuid.uuid4())
        return True

# ELK 스택 연동 (Elasticsearch, Logstash, Kibana)
"""
# Logstash 설정 예시
input {
  tcp {
    port => 5000
    codec => json
  }
}

filter {
  json {
    source => "message"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "aegis-logs-%{+YYYY.MM.dd}"
  }
}
"""

# Fluentd를 통한 로그 수집
"""
<source>
  @type forward
  port 24224
</source>

<match aegis.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  logstash_format true
  logstash_prefix aegis
</match>
"""

# 로그 레벨 기반 샘플링
import random

def sampled_log(log_func, sample_rate=0.1):
    """로그 샘플링 데코레이터"""
    def wrapper(message, *args, **kwargs):
        if random.random() < sample_rate:
            log_func(message, *args, **kwargs)
    return wrapper

# 디버그 로그는 10%만 기록
debug_logger = sampled_log(logger.debug, sample_rate=0.1)
```

**성능 개선 수치**:
- 로그 분석 시간: 70-90% 감소
- 디버깅 효율성: 5-10배 향상
- 로그 저장소 비용: 40-60% 감소 (샘플링 시)

**적용 시 주의사항**:
- 로그 포맷 표준화 필요
- 민감 정보 마스킹 필수
- 로그 볼륨 관리 (로그 로테이션, 보존 정책)

### 5.3 병목 지점 식별
**문제 상황**: 전체 시스템 성능 저하 원인 불분명
```python
# 성능 문제가 있는 코드
def process_data(data):
    result1 = step1(data)  # 어떤 단계가 느린지?
    result2 = step2(result1)
    result3 = step3(result2)
    return result3
```

**해결 방법**: 프로파일링 도구를 통한 정밀 분석
```python
import cProfile
import pstats
import io
from line_profiler import LineProfiler
import memory_profiler

# 1. cProfile을 이용한 함수 수준 프로파일링
def profile_function(func, *args, **kwargs):
    """함수 프로파일링 래퍼"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func(*args, **kwargs)
    
    profiler.disable()
    
    # 결과 분석
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # 상위 20개 함수
    
    print("=== Function Profile ===")
    print(s.getvalue())
    
    return result

# 사용 예시
profile_function(process_data, large_dataset)

# 2. line_profiler를 이용한 라인 단위 프로파일링
def line_profile_function():
    """라인 단위 프로파일링 데코레이터"""
    profiler = LineProfiler()
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            profiler.add_function(func)
            profiler.enable_by_count()
            
            result = func(*args, **kwargs)
            
            profiler.disable_by_count()
            profiler.print_stats()
            
            return result
        return wrapper
    return decorator

@line_profile_function()
def expensive_operation(data):
    total = 0
    for i in range(len(data)):  # 이 라인이 느린지 확인
        for j in range(len(data[i])):  # 중첩 루프 확인
            total += data[i][j] * complex_calculation(i, j)
    return total

# 3. 메모리 프로파일링
@memory_profiler.profile
def memory_intensive_operation():
    data = []
    for i in range(10000):
        # 메모리 사용 패턴 분석
        data.append([j for j in range(1000)])
    
    processed = process_large_data(data)
    return processed

# 4. 비동기 작업 프로파일링
import asyncio
import yappi  # 비동기 프로파일러

async def profile_async_task():
    yappi.start()  # 프로파일링 시작
    
    await asyncio.gather(
        task1(),
        task2(),
        task3()
    )
    
    yappi.stop()
    
    # 결과 출력
    print("=== Async Task Statistics ===")
    yappi.get_func_stats().print_all()
    yappi.get_thread_stats().print_all()

# 5. 데이터베이스 쿼리 프로파일링
# Django Debug Toolbar 설정
"""
INSTALLED_APPS = [
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

DEBUG_TOOLBAR_CONFIG = {
    'SQL_WARNING_THRESHOLD': 100,  # 100ms 이상 쿼리 경고
}
"""

# 쿼리 수 제한 및 경고
from django.db import connection
from django.test.utils import override_settings

class QueryCounter:
    """쿼리 수 모니터링"""
    def __enter__(self):
        self.initial_queries = len(connection.queries)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        final_queries = len(connection.queries)
        query_count = final_queries - self.initial_queries
        
        if query_count > 10:  # 허용 쿼리 수 초과
            print(f"WARNING: {query_count} queries executed")
            
            # 느린 쿼리 분석
            slow_queries = [q for q in connection.queries[self.initial_queries:] 
                          if float(q['time']) > 0.1]
            
            for q in slow_queries:
                print(f"Slow query ({q['time']}s): {q['sql'][:100]}...")

# 사용 예시
def optimized_view(request):
    with QueryCounter():
        # 뷰 로직 실행
        data = complex_operation()
        
    return Response(data)

# 6. 실시간 모니터링 대시보드
from django.http import JsonResponse
import psutil
import resource

@api_view(['GET'])
def system_metrics(request):
    """시스템 메트릭 API"""
    process = psutil.Process()
    
    metrics = {
        'cpu': {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
        },
        'memory': {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'percent': psutil.virtual_memory().percent,
            'process_rss': process.memory_info().rss,
        },
        'disk': {
            'usage': psutil.disk_usage('/').percent,
        },
        'database': {
            'connections': get_db_connection_count(),
        },
        'application': {
            'request_rate': get_request_rate(),
            'error_rate': get_error_rate(),
            'response_time_p95': get_response_time_percentile(95),
        }
    }
    
    return JsonResponse(metrics)
```

**성능 개선 수치**:
- 병목 지점 발견 시간: 일 → 시간 단위
- 최적화 효과 측정: 정량적 평가 가능
- 시스템 이해도: 획기적 향상

**적용 시 주의사항**:
- 프로파일링 도구 자체의 오버헤드 고려
- 프로덕션 환경에서의 프로파일링은 주의 필요
- 프로파일링 데이터 보안 관리

---

## 결론

AEGIS v3.1 백엔드 최적화는 단일 기술이 아닌 체계적인 접근이 필요합니다. 각 최적화 기법은 특정 문제 상황에 맞게 선택적 적용되어야 하며, 지속적인 모니터링과 프로파일링을 통해 효과를 검증해야 합니다.

**권장 적용 순서**:
1. 모니터링 인프라 구축 (APM, 로깅)
2. 데이터베이스 최적화 (인덱스, 쿼리)
3. 메모리 관리 최적화
4. 비동기 처리 도입
5. API 응답 최적화

각 최적화는 테스트 환경에서 검증 후 프로덕션에 적용하며, A/B 테스트를 통해 실제 성능 향상을 측정하는 것이 중요합니다.
