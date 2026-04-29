"""
Post-Match Analysis Workflow with Overnight Processing
Handles full match analysis with comprehensive reporting and batch processing
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict, field
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Import the integrated analyzer
from data_collection.integrated_analyzer import (
    process_volleyball_analysis, create_analysis_request, 
    AnalysisRequest, AnalysisResult
)
from data_collection.court_detector import detect_court_in_video, get_homography_matrix, transform_points, order_corners
from data_collection.visualiser import render_shot_map, render_heatmap

@dataclass
class MatchProcessingJob:
    """Represents a match processing job"""
    job_id: str
    video_path: str
    dvw_file_path: Optional[str]
    athlete_id: Optional[str]
    tournament_name: str
    match_date: datetime
    priority: str  # low, normal, high
    status: str  # pending, processing, completed, failed
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result_path: Optional[str]
    error_message: Optional[str]
    processing_time: Optional[float]
    quality_score: Optional[float]

@dataclass
class PostMatchReport:
    """Comprehensive post-match analysis report"""
    match_id: str
    athlete_id: Optional[str]
    tournament_name: str
    match_date: datetime
    analysis_timestamp: datetime
    
    # Layer 1: Tactical Summary
    tactical_summary: Dict
    rally_count: int
    serve_analysis: Dict
    attack_analysis: Dict
    reception_analysis: Dict
    transition_analysis: Dict
    
    # Layer 2: Biomechanical Summary
    biomechanical_summary: Dict
    actions_analyzed: int
    elite_deviations: List[Dict]
    position_specific_insights: Dict
    consistency_metrics: Dict
    
    # Layer 3: Integrated Insights
    integrated_insights: List[Dict]
    coaching_recommendations: List[Dict]
    training_priorities: List[str]
    competition_readiness: Dict
    
    # Overall Assessment
    overall_quality_score: float
    key_strengths: List[str]
    priority_improvements: List[str]
    next_match_preparation: List[str]
    
    # Training Program
    recommended_training_focus: str
    weekly_training_plan: Dict
    performance_targets: Dict
    progress_tracking_metrics: List[str]
    
    # Shot Map Data
    shot_map_data: List[Dict] = field(default_factory=list)
    shot_map_image_path: Optional[str] = None

class MatchProcessingQueue:
    """Manages match processing queue with priority and scheduling"""
    
    def __init__(self, db_path: str = "C:/sportsai-backend/data/match_processing.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for job tracking"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_jobs (
                job_id TEXT PRIMARY KEY,
                video_path TEXT NOT NULL,
                dvw_file_path TEXT,
                athlete_id TEXT,
                tournament_name TEXT,
                match_date TEXT,
                priority TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                result_path TEXT,
                error_message TEXT,
                processing_time REAL,
                quality_score REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_reports (
                match_id TEXT PRIMARY KEY,
                report_data TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_job(self, video_path: str, dvw_file_path: Optional[str] = None,
                athlete_id: Optional[str] = None, tournament_name: str = "Training",
                match_date: Optional[datetime] = None, priority: str = "normal") -> str:
        """Add new match processing job"""
        
        job_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{athlete_id or 'unknown'}"
        match_date = match_date or datetime.now()
        
        job = MatchProcessingJob(
            job_id=job_id,
            video_path=video_path,
            dvw_file_path=dvw_file_path,
            athlete_id=athlete_id,
            tournament_name=tournament_name,
            match_date=match_date,
            priority=priority,
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            result_path=None,
            error_message=None,
            processing_time=None,
            quality_score=None
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO processing_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.job_id, job.video_path, job.dvw_file_path, job.athlete_id,
            job.tournament_name, job.match_date.isoformat(), job.priority, job.status,
            job.created_at.isoformat(), None, None, None, None, None, None
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Added processing job: {job_id} for {video_path}")
        
        return job_id
    
    def get_next_job(self) -> Optional[MatchProcessingJob]:
        """Get next job to process based on priority and creation time"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get highest priority pending job (high > normal > low)
        cursor.execute('''
            SELECT * FROM processing_jobs 
            WHERE status = 'pending' 
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'normal' THEN 2 
                    WHEN 'low' THEN 3 
                END,
                created_at ASC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_job(row)
        
        return None
    
    def update_job_status(self, job_id: str, status: str, 
                         result_path: Optional[str] = None, 
                         error_message: Optional[str] = None,
                         processing_time: Optional[float] = None,
                         quality_score: Optional[float] = None):
        """Update job status and results"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        if status == "processing":
            cursor.execute('''
                UPDATE processing_jobs 
                SET status = ?, started_at = ?
                WHERE job_id = ?
            ''', (status, now.isoformat(), job_id))
        
        elif status in ["completed", "failed"]:
            cursor.execute('''
                UPDATE processing_jobs 
                SET status = ?, completed_at = ?, result_path = ?, 
                    error_message = ?, processing_time = ?, quality_score = ?
                WHERE job_id = ?
            ''', (status, now.isoformat(), result_path, error_message, 
                  processing_time, quality_score, job_id))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Updated job {job_id} status to {status}")
    
    def get_job_status(self, job_id: str) -> Optional[MatchProcessingJob]:
        """Get job status by ID"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM processing_jobs WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_job(row)
        
        return None
    
    def get_jobs_by_athlete(self, athlete_id: str, limit: int = 10) -> List[MatchProcessingJob]:
        """Get recent jobs for an athlete"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM processing_jobs 
            WHERE athlete_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (athlete_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_job(row) for row in rows]
    
    def _row_to_job(self, row) -> MatchProcessingJob:
        """Convert database row to MatchProcessingJob"""
        
        return MatchProcessingJob(
            job_id=row[0],
            video_path=row[1],
            dvw_file_path=row[2],
            athlete_id=row[3],
            tournament_name=row[4],
            match_date=datetime.fromisoformat(row[5]),
            priority=row[6],
            status=row[7],
            created_at=datetime.fromisoformat(row[8]),
            started_at=datetime.fromisoformat(row[9]) if row[9] else None,
            completed_at=datetime.fromisoformat(row[10]) if row[10] else None,
            result_path=row[11],
            error_message=row[12],
            processing_time=row[13],
            quality_score=row[14]
        )

class PostMatchAnalyzer:
    """Handles comprehensive post-match analysis"""
    
    def __init__(self, queue: MatchProcessingQueue):
        self.queue = queue
        self.logger = logging.getLogger(__name__)
        self.reports_dir = Path("C:/sportsai-backend/reports/post_match")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_match(self, job: MatchProcessingJob) -> PostMatchReport:
        """Process comprehensive match analysis"""
        
        self.logger.info(f"Processing match analysis for job: {job.job_id}")
        
        try:
            # Update job status
            self.queue.update_job_status(job.job_id, "processing")
            
            # Create analysis request
            request = create_analysis_request(
                video_path=job.video_path,
                dvw_file_path=job.dvw_file_path,
                athlete_id=job.athlete_id,
                tournament_context=job.tournament_name,
                analysis_level="elite"
            )
            
            # Perform comprehensive analysis
            start_time = datetime.now()
            analysis_result = await process_volleyball_analysis(request)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if analysis_result.status == 'failed':
                raise Exception(f"Analysis failed: {analysis_result.integrated_assessment.get('error', 'Unknown error')}")
            
            # Generate comprehensive report
            report = self.generate_post_match_report(job, analysis_result)
            
            # Save report
            report_path = self.save_report(report)
            
            # Update job with results
            self.queue.update_job_status(
                job_id=job.job_id,
                status="completed",
                result_path=str(report_path),
                processing_time=processing_time,
                quality_score=analysis_result.quality_score
            )
            
            self.logger.info(f"Match analysis completed: {job.job_id} ({processing_time:.1f}s, quality: {analysis_result.quality_score:.2f})")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Match analysis failed for job {job.job_id}: {e}")
            self.queue.update_job_status(
                job_id=job.job_id,
                status="failed",
                error_message=str(e)
            )
            raise
    
    def generate_post_match_report(self, job: MatchProcessingJob, analysis_result: AnalysisResult) -> PostMatchReport:
        """Generate comprehensive post-match report"""
        
        # Extract data from analysis result
        tactical_data = analysis_result.layer_1_tactical or {}
        biomechanical_data = analysis_result.layer_2_biomechanical or {}
        llm_data = analysis_result.layer_3_llm_insights or {}
        
        # Generate tactical summary
        tactical_summary = self.summarize_tactical_data(tactical_data)
        
        # Generate biomechanical summary
        biomechanical_summary = self.summarize_biomechanical_data(biomechanical_data)
        
        # Extract integrated insights
        integrated_insights = llm_data.get('contextual_insights', [])
        
        # Generate coaching recommendations
        coaching_recommendations = llm_data.get('training_recommendations', [])
        
        # Assess competition readiness
        competition_readiness = llm_data.get('competition_readiness', {})
        
        # Identify key strengths and improvements
        key_strengths = self.identify_key_strengths(analysis_result)
        priority_improvements = self.identify_priority_improvements(analysis_result)
        
        # Generate training program
        training_program = self.generate_training_program(coaching_recommendations, job.athlete_id)

        # ── 2D SHOT MAP GENERATION ──
        shot_map_data = []
        shot_map_path = None
        
        try:
            # 1. Detect court for homography
            court_result = detect_court_in_video(job.video_path, sample_every_n=60)
            if court_result["polygon"]:
                ordered = order_corners(court_result["polygon"])
                H = get_homography_matrix(ordered)
                
                # 2. Convert action coordinates to 2D
                # Assuming tactical_data has rally_analysis with ball_impact coordinates
                actions = []
                for rally in tactical_data.get("rally_analysis", []):
                    for event in rally.get("events", []):
                        if event.get("x") and event.get("y"):
                            # Convert video coords to 2D court meters
                            vid_pt = np.array([[event["x"], event["y"]]])
                            court_pt = transform_points(vid_pt, H)[0]
                            
                            action_item = {
                                "2d_coords": court_pt.tolist(),
                                "action_type": event.get("type", "unknown"),
                                "player_id": event.get("player_id"),
                                "frame": event.get("frame")
                            }
                            shot_map_data.append(action_item)
                
                # 3. Render map image
                if shot_map_data:
                    shot_map_filename = f"shot_map_{job.job_id}.jpg"
                    shot_map_path = self.reports_dir / shot_map_filename
                    render_shot_map(shot_map_data, str(shot_map_path))
        except Exception as e:
            self.logger.error(f"Failed to generate shot map: {e}")
        
        report = PostMatchReport(
            match_id=job.job_id,
            athlete_id=job.athlete_id,
            tournament_name=job.tournament_name,
            match_date=job.match_date,
            analysis_timestamp=datetime.now(),
            
            # Tactical data
            tactical_summary=tactical_summary,
            rally_count=len(tactical_data.get('rally_analysis', [])),
            serve_analysis=tactical_data.get('tactical_patterns', {}).get('serve', {}),
            attack_analysis=tactical_data.get('tactical_patterns', {}).get('attack', {}),
            reception_analysis=tactical_data.get('tactical_patterns', {}).get('reception', {}),
            transition_analysis=tactical_data.get('tactical_patterns', {}).get('transition', {}),
            
            # Biomechanical data
            biomechanical_summary=biomechanical_summary,
            actions_analyzed=biomechanical_data.get('actions_analyzed', 0),
            elite_deviations=biomechanical_data.get('elite_comparisons', {}),
            position_specific_insights=biomechanical_data.get('detected_positions', {}),
            consistency_metrics=biomechanical_data.get('quality_metrics', {}),
            
            # Integrated insights
            integrated_insights=integrated_insights,
            coaching_recommendations=coaching_recommendations,
            training_priorities=self.extract_training_priorities(coaching_recommendations),
            competition_readiness=competition_readiness,
            
            # Overall assessment
            overall_quality_score=analysis_result.quality_score or 0.0,
            key_strengths=key_strengths,
            priority_improvements=priority_improvements,
            next_match_preparation=self.generate_next_match_preparation(competition_readiness),
            
            # Training program
            recommended_training_focus=self.determine_training_focus(coaching_recommendations),
            weekly_training_plan=training_program.get('weekly_plan', {}),
            performance_targets=training_program.get('targets', {}),
            progress_tracking_metrics=training_program.get('metrics', []),

            # Shot Map
            shot_map_data=shot_map_data,
            shot_map_image_path=str(shot_map_path) if shot_map_path else None
        )
        
        return report
    
    def summarize_tactical_data(self, tactical_data: Dict) -> Dict:
        """Summarize tactical analysis data"""
        
        match_summary = tactical_data.get('match_summary', {})
        tactical_patterns = tactical_data.get('tactical_patterns', {})
        
        return {
            'total_actions': match_summary.get('total_actions', 0),
            'rally_count': match_summary.get('rally_count', 0),
            'match_duration_minutes': match_summary.get('match_duration', 0) / 60,
            'serve_effectiveness': self.calculate_serve_effectiveness(tactical_patterns.get('serve', {})),
            'attack_variety': self.calculate_attack_variety(tactical_patterns.get('attack', {})),
            'reception_quality': self.calculate_reception_quality(tactical_patterns.get('reception', {})),
            'transition_speed': self.calculate_transition_speed(tactical_patterns.get('transition', {}))
        }
    
    def summarize_biomechanical_data(self, biomechanical_data: Dict) -> Dict:
        """Summarize biomechanical analysis data"""
        
        elite_comparisons = biomechanical_data.get('elite_comparisons', {})
        quality_metrics = biomechanical_data.get('quality_metrics', {})
        
        # Calculate deviation statistics
        all_deviations = []
        for action_type, comparisons in elite_comparisons.items():
            for joint, data in comparisons.items():
                if 'deviation' in data:
                    all_deviations.append(abs(data['deviation']))
        
        return {
            'actions_analyzed': biomechanical_data.get('actions_analyzed', 0),
            'analysis_quality': quality_metrics.get('overall_quality', 0),
            'average_deviation_degrees': np.mean(all_deviations) if all_deviations else 0,
            'max_deviation_degrees': max(all_deviations) if all_deviations else 0,
            'consistency_score': quality_metrics.get('confidence_score', 0),
            'elite_alignment_percentage': self.calculate_elite_alignment(elite_comparisons)
        }
    
    def calculate_serve_effectiveness(self, serve_data: Dict) -> Dict:
        """Calculate serve effectiveness metrics"""
        
        zone_dist = serve_data.get('zone_distribution', {})
        quality_dist = serve_data.get('quality_distribution', {})
        
        total_serves = sum(zone_dist.values()) if zone_dist else 0
        
        return {
            'total_serves': total_serves,
            'zone_variety': len(zone_dist),
            'average_quality': np.mean(list(quality_dist.values())) if quality_dist else 0,
            'effectiveness_score': serve_data.get('effectiveness_score', 0)
        }
    
    def calculate_attack_variety(self, attack_data: Dict) -> Dict:
        """Calculate attack variety metrics"""
        
        tempo_dist = attack_data.get('tempo_distribution', {})
        zone_dist = attack_data.get('zone_distribution', {})
        
        return {
            'tempo_variety': len(tempo_dist),
            'zone_variety': len(zone_dist),
            'kill_rate_estimate': attack_data.get('kill_rate_estimate', 0),
            'tempo_effectiveness': attack_data.get('tempo_effectiveness', {})
        }
    
    def calculate_reception_quality(self, reception_data: Dict) -> Dict:
        """Calculate reception quality metrics"""
        
        quality_dist = reception_data.get('quality_distribution', {})
        perfect_rate = reception_data.get('perfect_pass_rate', 0)
        error_rate = reception_data.get('error_rate', 0)
        
        return {
            'perfect_pass_rate': perfect_rate,
            'error_rate': error_rate,
            'quality_distribution': quality_dist,
            'average_quality': np.mean(list(quality_dist.values())) if quality_dist else 0
        }
    
    def calculate_transition_speed(self, transition_data: Dict) -> Dict:
        """Calculate transition speed metrics"""
        
        avg_time = transition_data.get('average_transition_time', 0)
        time_dist = transition_data.get('transition_time_distribution', {})
        
        return {
            'average_transition_time': avg_time,
            'transition_consistency': time_dist.get('std', 0) if time_dist else 0,
            'quality_impact': transition_data.get('quality_impact', {})
        }
    
    def calculate_elite_alignment(self, elite_comparisons: Dict) -> float:
        """Calculate percentage of measurements within elite ranges"""
        
        total_measurements = 0
        elite_measurements = 0
        
        for action_type, comparisons in elite_comparisons.items():
            for joint, data in comparisons.items():
                if 'assessment' in data:
                    total_measurements += 1
                    if data['assessment'] in ['elite', 'good']:
                        elite_measurements += 1
        
        return (elite_measurements / total_measurements * 100) if total_measurements > 0 else 0
    
    def identify_key_strengths(self, analysis_result: AnalysisResult) -> List[str]:
        """Identify athlete's key strengths from analysis"""
        
        strengths = []
        
        # Check tactical strengths
        tactical_data = analysis_result.layer_1_tactical or {}
        serve_patterns = tactical_data.get('tactical_patterns', {}).get('serve', {})
        
        if serve_patterns.get('effectiveness_score', 0) > 0.7:
            strengths.append("Strong serve effectiveness and placement variety")
        
        # Check biomechanical strengths
        biomechanical_data = analysis_result.layer_2_biomechanical or {}
        if biomechanical_data.get('quality_metrics', {}).get('overall_quality', 0) > 0.8:
            strengths.append("Consistent biomechanical execution across actions")
        
        # Check integrated strengths
        llm_data = analysis_result.layer_3_llm_insights or {}
        competition_readiness = llm_data.get('competition_readiness', {})
        
        if competition_readiness.get('overall_readiness', 0) > 0.8:
            strengths.append("High competition readiness level")
        
        return strengths if strengths else ["Solid fundamental skills across all areas"]
    
    def identify_priority_improvements(self, analysis_result: AnalysisResult) -> List[str]:
        """Identify priority areas for improvement"""
        
        improvements = []
        
        # Check tactical areas
        tactical_data = analysis_result.layer_1_tactical or {}
        tactical_patterns = tactical_data.get('tactical_patterns', {})
        
        # Serve improvements
        serve_data = tactical_patterns.get('serve', {})
        if serve_data.get('effectiveness_score', 1.0) < 0.6:
            improvements.append("Serve consistency and target accuracy")
        
        # Attack improvements
        attack_data = tactical_patterns.get('attack', {})
        tempo_dist = attack_data.get('tempo_distribution', {})
        if tempo_dist.get('high_ball', 0) > 0.7:
            improvements.append("Incorporate faster tempo attacks for variety")
        
        # Check biomechanical areas
        biomechanical_data = analysis_result.layer_2_biomechanical or {}
        elite_comparisons = biomechanical_data.get('elite_comparisons', {})
        
        # Find consistent biomechanical issues
        all_deviations = []
        for action_type, comparisons in elite_comparisons.items():
            for joint, data in comparisons.items():
                if data.get('assessment') == 'needs_improvement':
                    all_deviations.append(f"{joint} in {action_type}")
        
        if all_deviations:
            # Get most common issues
            from collections import Counter
            deviation_counts = Counter(all_deviations)
            top_issues = [issue for issue, count in deviation_counts.most_common(3)]
            improvements.extend(top_issues)
        
        return improvements if improvements else ["Continue refining technical execution"]
    
    def generate_next_match_preparation(self, competition_readiness: Dict) -> List[str]:
        """Generate next match preparation recommendations"""
        
        readiness_level = competition_readiness.get('readiness_level', 'development_needed')
        
        preparation_recommendations = {
            'competition_ready': [
                "Maintain current training intensity",
                "Focus on mental preparation and visualization",
                "Review tactical game plan for next opponent"
            ],
            'near_ready': [
                "Address identified technical issues in practice",
                "Increase competition-specific training scenarios",
                "Focus on consistency in key skill areas"
            ],
            'development_needed': [
                "Prioritize fundamental skill development",
                "Work on identified biomechanical corrections",
                "Build confidence through successful repetitions"
            ],
            'significant_work_needed': [
                "Comprehensive technical development program",
                "Focus on basic movement patterns and mechanics",
                "Extended preparation timeline recommended"
            ]
        }
        
        return preparation_recommendations.get(readiness_level, ["Continue skill development"])
    
    def determine_training_focus(self, coaching_recommendations: List[Dict]) -> str:
        """Determine primary training focus from recommendations"""
        
        high_priority_recs = [rec for rec in coaching_recommendations if rec.get('priority') == 'high']
        
        if high_priority_recs:
            categories = [rec.get('category', 'general') for rec in high_priority_recs]
            most_common = max(set(categories), key=categories.count) if categories else 'general'
            
            focus_mapping = {
                'serve': 'Serve consistency and placement accuracy',
                'attack': 'Attack variety and tempo execution',
                'reception': 'Reception platform and footwork fundamentals',
                'block': 'Block timing and penetration technique',
                'defense': 'Defensive positioning and ball control',
                'general': 'Overall technical consistency and execution'
            }
            
            return focus_mapping.get(most_common, 'Comprehensive skill development')
        
        return 'Maintain current training focus areas'
    
    def generate_training_program(self, coaching_recommendations: List[Dict], athlete_id: Optional[str]) -> Dict:
        """Generate 8-week training program based on recommendations"""
        
        # Filter high-priority recommendations
        priority_recs = [rec for rec in coaching_recommendations if rec.get('priority') in ['high', 'medium']]
        
        # Generate weekly plan
        weekly_plan = {
            'week_1': {'focus': 'Assessment and fundamentals', 'intensity': 'moderate'},
            'week_2': {'focus': 'Technique refinement', 'intensity': 'moderate'},
            'week_3': {'focus': 'Consistency development', 'intensity': 'high'},
            'week_4': {'focus': 'Integration and speed', 'intensity': 'high'},
            'week_5': {'focus': 'Competition simulation', 'intensity': 'very_high'},
            'week_6': {'focus': 'Pressure training', 'intensity': 'very_high'},
            'week_7': {'focus': 'Fine-tuning and recovery', 'intensity': 'moderate'},
            'week_8': {'focus': 'Competition preparation', 'intensity': 'peak'}
        }
        
        # Set performance targets based on recommendations
        targets = {
            'serve_accuracy_target': 75,  # percentage
            'attack_kill_rate_target': 45,  # percentage
            'reception_quality_target': 2.5,  # average quality (1-3)
            'consistency_improvement_target': 20,  # percentage improvement
            'biomechanical_deviation_reduction': 30  # percentage reduction
        }
        
        # Progress tracking metrics
        metrics = [
            'Serve accuracy percentage',
            'Attack kill rate',
            'Reception average quality',
            'Biomechanical consistency score',
            'Competition readiness level',
            'Training session completion rate'
        ]
        
        return {
            'weekly_plan': weekly_plan,
            'targets': targets,
            'metrics': metrics,
            'priority_recommendations': priority_recs
        }
    
    def extract_training_priorities(self, coaching_recommendations: List[Dict]) -> List[str]:
        """Extract training priorities from coaching recommendations"""
        
        priorities = []
        
        for rec in coaching_recommendations:
            if rec.get('priority') == 'high':
                category = rec.get('category', 'general')
                focus_area = rec.get('focus_area', 'fundamentals')
                priorities.append(f"{category}: {focus_area}")
        
        return priorities[:5]  # Top 5 priorities
    
    def save_report(self, report: PostMatchReport) -> Path:
        """Save post-match report to file"""
        
        # Generate filename
        athlete_suffix = f"_{report.athlete_id}" if report.athlete_id else ""
        filename = f"post_match_report_{report.match_date.strftime('%Y%m%d')}{athlete_suffix}_{report.match_id}.json"
        report_path = self.reports_dir / filename
        
        # Convert to dict and save
        report_dict = asdict(report)
        
        with open(report_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        self.logger.info(f"Saved post-match report: {report_path}")
        
        return report_path

class OvernightProcessor:
    """Handles overnight batch processing of matches"""
    
    def __init__(self, max_concurrent_jobs: int = 2):
        self.queue = MatchProcessingQueue()
        self.analyzer = PostMatchAnalyzer(self.queue)
        self.logger = logging.getLogger(__name__)
        self.max_concurrent_jobs = max_concurrent_jobs
        self.is_running = False
    
    async def start_overnight_processing(self):
        """Start overnight processing loop"""
        
        self.logger.info("Starting overnight processing service")
        self.is_running = True
        
        while self.is_running:
            try:
                # Get next job to process
                job = self.queue.get_next_job()
                
                if job:
                    self.logger.info(f"Processing overnight job: {job.job_id}")
                    
                    # Process the match
                    await self.analyzer.process_match(job)
                    
                    # Small delay between jobs
                    await asyncio.sleep(30)
                
                else:
                    # No jobs available, wait longer
                    self.logger.info("No pending jobs, waiting 5 minutes")
                    await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in overnight processing: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_overnight_processing(self):
        """Stop overnight processing"""
        
        self.logger.info("Stopping overnight processing service")
        self.is_running = False
    
    def get_processing_status(self) -> Dict:
        """Get current processing status"""
        
        conn = sqlite3.connect(self.queue.db_path)
        cursor = conn.cursor()
        
        # Get job statistics
        cursor.execute('SELECT status, COUNT(*) FROM processing_jobs GROUP BY status')
        status_counts = dict(cursor.fetchall())
        
        # Get recent completed jobs
        cursor.execute('''
            SELECT job_id, athlete_id, tournament_name, completed_at, quality_score 
            FROM processing_jobs 
            WHERE status = 'completed' 
            ORDER BY completed_at DESC 
            LIMIT 5
        ''')
        recent_completed = cursor.fetchall()
        
        # Get processing queue size
        cursor.execute('SELECT COUNT(*) FROM processing_jobs WHERE status = "pending"')
        pending_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'is_running': self.is_running,
            'job_statistics': status_counts,
            'pending_jobs': pending_count,
            'recent_completed': [
                {
                    'job_id': row[0],
                    'athlete_id': row[1],
                    'tournament': row[2],
                    'completed_at': row[3],
                    'quality_score': row[4]
                }
                for row in recent_completed
            ]
        }

class ReportNotifier:
    """Handles notifications for completed analysis reports"""
    
    def __init__(self, smtp_config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)
        self.smtp_config = smtp_config or {}
    
    def send_report_notification(self, report: PostMatchReport, recipient_email: str) -> bool:
        """Send email notification with report summary"""
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get('from_email', 'noreply@sportsai.com')
            msg['To'] = recipient_email
            msg['Subject'] = f"Post-Match Analysis Report - {report.tournament_name}"
            
            # Create email body
            body = self.create_report_email_body(report)
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach report file if available
            if hasattr(report, 'report_path') and Path(report.report_path).exists():
                with open(report.report_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {Path(report.report_path).name}'
                    )
                    msg.attach(part)
            
            # Send email (placeholder - would use actual SMTP)
            self.logger.info(f"Would send email notification to {recipient_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False
    
    def create_report_email_body(self, report: PostMatchReport) -> str:
        """Create email body text from report"""
        
        body = f"""
Post-Match Analysis Report
==========================

Tournament: {report.tournament_name}
Match Date: {report.match_date.strftime('%Y-%m-%d')}
Analysis Date: {report.analysis_timestamp.strftime('%Y-%m-%d %H:%M')}
Overall Quality Score: {report.overall_quality_score:.1f}/1.0

Key Findings:
- Actions Analyzed: {report.actions_analyzed}
- Rally Count: {report.rally_count}
- Competition Readiness: {report.competition_readiness.get('readiness_level', 'Unknown')}

Key Strengths:
{chr(10).join(f"- {strength}" for strength in report.key_strengths)}

Priority Improvements:
{chr(10).join(f"- {improvement}" for improvement in report.priority_improvements[:3])}

Training Focus: {report.recommended_training_focus}

Next Match Preparation:
{chr(10).join(f"- {prep}" for prep in report.next_match_preparation[:3])}

For detailed analysis and training recommendations, please review the full report.

Best regards,
SportsAI Analysis Team
"""
        
        return body.strip()

# Global instances for easy access
processing_queue = MatchProcessingQueue()
post_match_analyzer = PostMatchAnalyzer(processing_queue)
overnight_processor = OvernightProcessor()
report_notifier = ReportNotifier()

async def submit_match_for_analysis(
    video_path: str,
    dvw_file_path: Optional[str] = None,
    athlete_id: Optional[str] = None,
    tournament_name: str = "Training",
    match_date: Optional[datetime] = None,
    priority: str = "normal",
    notify_email: Optional[str] = None
) -> str:
    """Submit a match for post-match analysis"""
    
    # Add job to queue
    job_id = processing_queue.add_job(
        video_path=video_path,
        dvw_file_path=dvw_file_path,
        athlete_id=athlete_id,
        tournament_name=tournament_name,
        match_date=match_date,
        priority=priority
    )
    
    # Schedule notification if email provided
    if notify_email:
        # This would be handled by the processing completion
        pass
    
    return job_id

def get_job_status(job_id: str) -> Optional[Dict]:
    """Get status of a processing job"""
    
    job = processing_queue.get_job_status(job_id)
    if job:
        return {
            'job_id': job.job_id,
            'status': job.status,
            'video_path': job.video_path,
            'athlete_id': job.athlete_id,
            'tournament_name': job.tournament_name,
            'match_date': job.match_date.isoformat(),
            'priority': job.priority,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'processing_time': job.processing_time,
            'quality_score': job.quality_score,
            'error_message': job.error_message,
            'result_path': job.result_path
        }
    
    return None

def get_athlete_reports(athlete_id: str, limit: int = 5) -> List[Dict]:
    """Get recent analysis reports for an athlete"""
    
    jobs = processing_queue.get_jobs_by_athlete(athlete_id, limit)
    
    reports = []
    for job in jobs:
        if job.status == 'completed' and job.result_path:
            try:
                with open(job.result_path, 'r') as f:
                    report_data = json.load(f)
                    reports.append({
                        'job_id': job.job_id,
                        'match_date': job.match_date.isoformat(),
                        'tournament_name': job.tournament_name,
                        'quality_score': job.quality_score,
                        'report_summary': {
                            'overall_quality_score': report_data.get('overall_quality_score'),
                            'key_strengths': report_data.get('key_strengths', [])[:3],
                            'priority_improvements': report_data.get('priority_improvements', [])[:3],
                            'competition_readiness': report_data.get('competition_readiness', {}).get('readiness_level')
                        }
                    })
            except Exception as e:
                logging.error(f"Error loading report for job {job.job_id}: {e}")
    
    return reports

async def start_overnight_processing_service():
    """Start the overnight processing service"""
    await overnight_processor.start_overnight_processing()

def stop_overnight_processing_service():
    """Stop the overnight processing service"""
    overnight_processor.stop_overnight_processing()

def get_processing_service_status() -> Dict:
    """Get status of the overnight processing service"""
    return overnight_processor.get_processing_status()