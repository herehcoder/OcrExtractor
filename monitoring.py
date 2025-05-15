import time
import logging
import threading
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta

# Configuração de logging
logger = logging.getLogger(__name__)

class APIMonitor:
    """
    Classe para monitorar o uso da API, coletando métricas e estatísticas
    """
    
    def __init__(self, window_size=1000):
        """
        Inicializa o sistema de monitoramento
        
        Args:
            window_size: Número máximo de requisições para manter no histórico
        """
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.request_times = deque(maxlen=window_size)
        self.request_times_by_endpoint = defaultdict(lambda: deque(maxlen=window_size))
        self.errors_by_type = defaultdict(int)
        self.requests_by_status = defaultdict(int)
        self.requests_by_endpoint = defaultdict(int)
        self.requests_by_hour = defaultdict(int)
        self.requests_by_date = defaultdict(int)
        self.requests_by_ip = defaultdict(int)
        self.file_sizes_processed = deque(maxlen=window_size)
        self.lock = threading.RLock()  # Para thread-safety
        
        # Estatísticas específicas para OCR
        self.ocr_processing_times = deque(maxlen=window_size)
        self.ocr_success_rate = 1.0
        self.ocr_by_language = defaultdict(int)
        self.ocr_by_document_type = defaultdict(int)
        
        # Dados da última hora e último dia (para cálculos em tempo real)
        self.last_hour_times = []
        self.last_day_times = []
        self.last_hour_errors = 0
        self.last_day_errors = 0
        self.last_reset = time.time()
    
    def record_request(self, endpoint, status_code, duration_ms, ip=None):
        """
        Registra informações sobre uma requisição
        
        Args:
            endpoint: Endpoint da API (ex: /ocr/upload)
            status_code: Código de status HTTP
            duration_ms: Duração da requisição em milissegundos
            ip: Endereço IP do cliente (opcional)
        """
        with self.lock:
            current_time = time.time()
            current_hour = datetime.now().strftime('%Y-%m-%d %H:00')
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Contagens gerais
            self.total_requests += 1
            if 200 <= status_code < 400:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                self.errors_by_type[status_code] += 1
            
            # Armazenar tempo de requisição
            self.request_times.append(duration_ms)
            self.request_times_by_endpoint[endpoint].append(duration_ms)
            
            # Atualizar contagens por status, endpoint e data
            self.requests_by_status[status_code] += 1
            self.requests_by_endpoint[endpoint] += 1
            self.requests_by_hour[current_hour] += 1
            self.requests_by_date[current_date] += 1
            
            # Armazenar IP se fornecido
            if ip:
                self.requests_by_ip[ip] += 1
            
            # Atualizar estatísticas de tempo real
            self.last_hour_times.append((current_time, duration_ms))
            self.last_day_times.append((current_time, duration_ms))
            
            if status_code >= 400:
                self.last_hour_errors += 1
                self.last_day_errors += 1
            
            # Limpar dados antigos (mais de 1 hora/dia)
            one_hour_ago = current_time - 3600
            one_day_ago = current_time - 86400
            
            self.last_hour_times = [(t, d) for t, d in self.last_hour_times if t >= one_hour_ago]
            self.last_day_times = [(t, d) for t, d in self.last_day_times if t >= one_day_ago]
            
            # Verificar se precisamos resetar os contadores de erros
            if current_time - self.last_reset > 3600:  # 1 hora
                self.last_hour_errors = sum(1 for t, _ in self.last_hour_times if t >= one_hour_ago)
                self.last_day_errors = sum(1 for t, _ in self.last_day_times if t >= one_day_ago)
                self.last_reset = current_time
    
    def record_ocr_processing(self, duration_ms, success, language, document_type, file_size=None):
        """
        Registra informações sobre o processamento OCR
        
        Args:
            duration_ms: Duração do processamento em milissegundos
            success: True se o OCR foi bem-sucedido, False se falhou
            language: Idioma utilizado para OCR
            document_type: Tipo de documento processado
            file_size: Tamanho do arquivo em bytes (opcional)
        """
        with self.lock:
            self.ocr_processing_times.append(duration_ms)
            
            # Atualizar contagens por idioma e tipo de documento
            self.ocr_by_language[language] += 1
            self.ocr_by_document_type[document_type] += 1
            
            # Armazenar tamanho do arquivo
            if file_size:
                self.file_sizes_processed.append(file_size)
            
            # Atualizar taxa de sucesso de OCR
            total_ocr = len(self.ocr_processing_times)
            if total_ocr > 0:
                success_ratio = self.successful_requests / total_ocr
                # Suavizar a média para evitar mudanças bruscas
                self.ocr_success_rate = 0.9 * self.ocr_success_rate + 0.1 * success_ratio
    
    def get_stats(self):
        """
        Retorna estatísticas gerais sobre o uso da API
        
        Returns:
            dict: Estatísticas de uso
        """
        with self.lock:
            # Calcular estatísticas de tempo de resposta
            avg_response_time = 0
            median_response_time = 0
            p95_response_time = 0
            
            if self.request_times:
                times_list = list(self.request_times)
                avg_response_time = sum(times_list) / len(times_list)
                median_response_time = statistics.median(times_list)
                p95_response_time = statistics.quantiles(times_list, n=20)[-1]  # 95th percentile
            
            # Calcular taxas de erro
            error_rate = 0
            if self.total_requests > 0:
                error_rate = self.failed_requests / self.total_requests
            
            # Calcular requisições na última hora
            hourly_request_count = len(self.last_hour_times)
            hourly_error_rate = 0
            if hourly_request_count > 0:
                hourly_error_rate = self.last_hour_errors / hourly_request_count
            
            # Calcular requisições nas últimas 24 horas
            daily_request_count = len(self.last_day_times)
            daily_error_rate = 0
            if daily_request_count > 0:
                daily_error_rate = self.last_day_errors / daily_request_count
            
            # Endpoint mais requisitado
            top_endpoint = "N/A"
            top_endpoint_count = 0
            if self.requests_by_endpoint:
                top_endpoint = max(self.requests_by_endpoint.items(), key=lambda x: x[1])[0]
                top_endpoint_count = self.requests_by_endpoint[top_endpoint]
            
            # Tamanho médio de arquivo
            avg_file_size = 0
            if self.file_sizes_processed:
                avg_file_size = sum(self.file_sizes_processed) / len(self.file_sizes_processed)
            
            # Informações de OCR
            avg_ocr_time = 0
            if self.ocr_processing_times:
                avg_ocr_time = sum(self.ocr_processing_times) / len(self.ocr_processing_times)
            
            # Estatísticas por idioma e tipo de documento
            top_language = "N/A"
            top_document_type = "N/A"
            
            if self.ocr_by_language:
                top_language = max(self.ocr_by_language.items(), key=lambda x: x[1])[0]
            
            if self.ocr_by_document_type:
                top_document_type = max(self.ocr_by_document_type.items(), key=lambda x: x[1])[0]
            
            return {
                "general": {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "error_rate": round(error_rate * 100, 2),
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "median_response_time_ms": round(median_response_time, 2),
                    "p95_response_time_ms": round(p95_response_time, 2)
                },
                "realtime": {
                    "hourly_requests": hourly_request_count,
                    "hourly_error_rate": round(hourly_error_rate * 100, 2),
                    "daily_requests": daily_request_count,
                    "daily_error_rate": round(daily_error_rate * 100, 2)
                },
                "endpoints": {
                    "top_endpoint": top_endpoint,
                    "top_endpoint_count": top_endpoint_count,
                    "endpoint_counts": dict(self.requests_by_endpoint)
                },
                "ocr": {
                    "ocr_success_rate": round(self.ocr_success_rate * 100, 2),
                    "avg_ocr_processing_time_ms": round(avg_ocr_time, 2),
                    "top_language": top_language,
                    "top_document_type": top_document_type,
                    "avg_file_size_bytes": round(avg_file_size, 2)
                },
                "errors": {
                    "error_counts_by_type": dict(self.errors_by_type)
                }
            }
    
    def get_detailed_stats(self, days=7):
        """
        Retorna estatísticas detalhadas com dados históricos
        
        Args:
            days: Número de dias para histórico
        
        Returns:
            dict: Estatísticas detalhadas
        """
        with self.lock:
            # Calcular datas para o período solicitado
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Filtrar dados para o período
            dates_in_range = []
            date = start_date
            while date <= end_date:
                date_str = date.strftime('%Y-%m-%d')
                dates_in_range.append(date_str)
                date += timedelta(days=1)
            
            # Preparar dados de requisições por dia
            requests_history = []
            for date_str in dates_in_range:
                requests_history.append({
                    "date": date_str,
                    "count": self.requests_by_date.get(date_str, 0)
                })
            
            # Estatísticas por endpoint
            endpoint_stats = []
            for endpoint, count in sorted(self.requests_by_endpoint.items(), key=lambda x: x[1], reverse=True):
                avg_time = 0
                if endpoint in self.request_times_by_endpoint and self.request_times_by_endpoint[endpoint]:
                    avg_time = sum(self.request_times_by_endpoint[endpoint]) / len(self.request_times_by_endpoint[endpoint])
                
                endpoint_stats.append({
                    "endpoint": endpoint,
                    "count": count,
                    "avg_response_time_ms": round(avg_time, 2)
                })
            
            # Estatísticas por idioma
            language_stats = []
            for language, count in sorted(self.ocr_by_language.items(), key=lambda x: x[1], reverse=True):
                language_stats.append({
                    "language": language,
                    "count": count,
                    "percentage": round(count / sum(self.ocr_by_language.values()) * 100, 2) if self.ocr_by_language else 0
                })
            
            # Estatísticas por tipo de documento
            document_stats = []
            for doc_type, count in sorted(self.ocr_by_document_type.items(), key=lambda x: x[1], reverse=True):
                document_stats.append({
                    "document_type": doc_type,
                    "count": count,
                    "percentage": round(count / sum(self.ocr_by_document_type.values()) * 100, 2) if self.ocr_by_document_type else 0
                })
            
            return {
                "date_range": {
                    "start": start_date.strftime('%Y-%m-%d'),
                    "end": end_date.strftime('%Y-%m-%d')
                },
                "request_history": requests_history,
                "endpoint_stats": endpoint_stats,
                "language_stats": language_stats,
                "document_stats": document_stats
            }

# Instância global para uso em toda a aplicação
api_monitor = APIMonitor()