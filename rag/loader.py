"""
Módulo de carga de datos desde múltiples APIs:
- GitHub API (documentos .md)
- Supabase API (Dashboard, Web Ventas)
- Neon DB (Campaña)
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
import supabase
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ============================================
# CONFIGURACIÓN - Credenciales
# ============================================

@dataclass
class DuneConfig:
    """Configuración centralizada del chatbot"""
    
    # GitHub
    github_org = "DUNE-ORGANIZATION-JJCA"
    github_repos = {
        "documentacion": "Dune-Documentacion",
        "juego": "Dune-Arrakis-Dominion",
        "landing": "Dune-Landing-Page",
        "web_ventas": "Dune-Web-Page",
    }
    
    # Supabase Dashboard
    supabase_dashboard_url = "https://jshzonryarokhquoazmy.supabase.co"
    supabase_dashboard_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpzaHpvbnJ5YXJva2hxdW9hem15Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2OTM2NDIsImV4cCI6MjA5MjI2OTY0Mn0.wOrhlsEHnFUHmrB0Hr85QR8rck6cDqr7CxAeae9vJj4"
    
    # Supabase Web Ventas
    supabase_ventas_url = "https://mlwriavicqpnrilusmkk.supabase.co"
    supabase_ventas_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1sd3JpYXZpY3FwbnJpbHVzbWtrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2ODIyNzEsImV4cCI6MjA5MjI1ODI3MX0.S74yQdD4-aApOAT35YSAodQGXLkUv_whi_4_gT94wb8"
    
    # Neon Campaña
    neon_connection_string = "postgresql://neondb_owner:npg_u4HxQmsKZMG1@ep-jolly-glade-alwj6pos-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


# ============================================
# GITHUB API - Cargar documentos .md
# ============================================

class GitHubLoader:
    """Carga documentos desde GitHub API"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, repo: str, config: DuneConfig = None):
        self.repo = repo
        self.config = config or DuneConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Dune-Chatbot-RAG"
        })
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Obtiene el contenido de un archivo"""
        url = f"{self.BASE_URL}/repos/{self.config.github_org}/{self.repo}/contents/{file_path}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Decodificar contenido base64
            import base64
            content = data.get("content", "")
            if content:
                return base64.b64decode(content).decode("utf-8")
            
            return None
            
        except Exception as e:
            logger.error(f"Error cargando {file_path}: {e}")
            return None
    
    def list_markdown_files(self, path: str = "") -> List[Dict[str, str]]:
        """Lista archivos .md en un directorio"""
        url = f"{self.BASE_URL}/repos/{self.config.github_org}/{self.repo}/contents/{path}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            contents = response.json()
            if not isinstance(contents, list):
                contents = [contents]
            
            md_files = []
            for item in contents:
                if item.get("type") == "file" and item.get("name", "").endswith(".md"):
                    md_files.append({
                        "name": item["name"],
                        "path": item["path"],
                        "url": item.get("download_url")
                    })
            
            return md_files
            
        except Exception as e:
            logger.error(f"Error listando archivos: {e}")
            return []
    
    def load_all_documents(self, repo_files: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Carga múltiples documentos
        
        Args:
            repo_files: {
                "Dune-Documentacion": ["path/to/doc1.md", "path/to/doc2.md"],
                "Dune-Landing-Page": ["index.html"],
                ...
            }
        
        Returns:
            {"repo:filename": "contenido"}
        """
        documents = {}
        
        for repo_name, files in repo_files.items():
            loader = GitHubLoader(repo_name, self.config)
            
            for file_path in files:
                # Es HTML o MD?
                if file_path.endswith(".html"):
                    content = self._load_html_from_github(repo_name, file_path)
                else:
                    content = loader.get_file_content(file_path)
                
                if content:
                    key = f"{repo_name}:{file_path}"
                    documents[key] = content
                    logger.info(f"Cargado: {key}")
        
        return documents
    
    def _load_html_from_github(self, repo: str, file_path: str) -> Optional[str]:
        """Carga archivo HTML desde GitHub"""
        url = f"{self.BASE_URL}/repos/{self.config.github_org}/{repo}/contents/{file_path}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            import base64
            content = data.get("content", "")
            if content:
                return base64.b64decode(content).decode("utf-8")
            
            return None
            
        except Exception as e:
            logger.error(f"Error cargando HTML {file_path}: {e}")
            return None


# ============================================
# SUPABASE API - Dashboard y Web Ventas
# ============================================

class SupabaseLoader:
    """Carga datos desde Supabase"""
    
    def __init__(self, url: str, key: str):
        self.client = supabase.create_client(url, key)
    
    def get_registros_beta(self) -> List[Dict]:
        """Obtiene registros de beta"""
        try:
            response = self.client.table("registros_beta").select("*").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error obteniendo registros: {e}")
            return []
    
    def get_sesiones(self, limit: int = 100) -> List[Dict]:
        """Obtiene sesiones web"""
        try:
            response = self.client.table("sesiones_web").select("*").limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error obteniendo sesiones: {e}")
            return []
    
    def get_metricas_video(self) -> List[Dict]:
        """Obtiene métricas de video"""
        try:
            response = self.client.table("metricas_video").select("*").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return []
    
    def get_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales"""
        stats = {
            "total_registros": 0,
            "total_sesiones": 0,
            "dispositivos": {},
            "paises": {}
        }
        
        try:
            # Contar registros
            response = self.client.table("registros_beta").select("*", count="exact").execute()
            stats["total_registros"] = response.count or 0
            
            # Contar sesiones
            response = self.client.table("sesiones_web").select("*", count="exact").execute()
            stats["total_sesiones"] = response.count or 0
            
        except Exception as e:
            logger.error(f"Error en estadísticas: {e}")
        
        return stats


# ============================================
# NEON DB - Campaña
# ============================================

class NeonLoader:
    """Carga datos desde Neon (PostgreSQL)"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def get_campaign_data(self) -> Dict[str, Any]:
        """
        Obtiene datos de la campaña
        Nota: Neon es PostgreSQL, necesitamos psycopg2 para conectar
        """
        # Por ahora retornamos estructura básica
        # La conexión real se hace en generator.py
        return {
            "status": "pending_connection",
            "note": "Neon requiere conexión PostgreSQL directa"
        }


# ============================================
# LOADERS FACTORY
# ============================================

def get_all_loaders(config: DuneConfig = None) -> Dict[str, Any]:
    """Inicializa todos los loaders"""
    cfg = config or DuneConfig()
    
    return {
        "github": GitHubLoader("Dune-Documentacion", cfg),
        "supabase_dashboard": SupabaseLoader(
            cfg.supabase_dashboard_url, 
            cfg.supabase_dashboard_key
        ),
        "supabase_ventas": SupabaseLoader(
            cfg.supabase_ventas_url,
            cfg.supabase_ventas_key
        ),
        "neon": NeonLoader(cfg.neon_connection_string)
    }


# ============================================
# DATOS DEL JUEGO - Documentos a cargar
# ============================================

# Archivos específicos por repositorio
REPO_FILES = {
    "Dune-Documentacion": [
        "Dune_Arrakis_Dominion_Storytelling.md",
        "Dune_Arrakis_Dominion_Manual_Tecnico.md",
        "Dune_Arrakis_Dominion_GDD_Recursos.md",
    ],
    "Dune-Landing-Page": [
        "index.html"
    ],
    "Dune-Web-Page": [
        "index.html"
    ]
}