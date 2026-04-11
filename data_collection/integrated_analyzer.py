"""
Integrated Three-Layer Architecture for Volleyball Analysis
Combines Tactical (Data Volley), Biomechanical (SAM2 + ViTPose), and LLM layers
Provides Olympic-grade comprehensive analysis
"""

import asyncio
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Import all the specialized modules
from data_collection.temporal_action_localizer import detect_volleyball_actions, ActionSegment
from data_collection.multi_player_tracker import track_multiple_players, PlayerTrack, VolleyballMultiTracker
from data_collection.tactical_analyzer import analyze_tactical_match, integrate_tactical_biomechanical, TacticalAnalyzer
from data_collection.llm_training_pipeline import create_training_pair_from_analysis, generate_llm_training_dataset
from data_collection.elite_biomechanics import get_elite_benchmark, detect_position_from_movement

@dataclass
class AnalysisRequest:
    """Request for comprehensive volleyball analysis"""
    video_path: str
    dvw_file_path: Optional[str] = None
    athlete_id: Optional[str] = None
    tournament_context: str = "training"
    analysis_level: str = "elite"  # basic, advanced, elite
    include_training_program: bool = True
    processing_priority: str = "normal"  # low, normal, high
    output_format: str = "comprehensive"  # summary, detailed, comprehensive

@dataclass
class AnalysisResult:
    """Comprehensive analysis result"""
    request_id: str
    timestamp: datetime
    status: str  # pending, processing, completed, failed
    layer_1_tactical: Optional[Dict] = None
    layer_2_biomechanical: Optional[Dict] = None
    layer_3_llm_insights: Optional[Dict] = None
    integrated_assessment: Optional[Dict] = None
    training_recommendations: Optional[List[Dict]] = None
    competition_readiness: Optional[Dict] = None
    processing_time: Optional[float] = None
    quality_score: Optional[float] = None

class Layer1TacticalProcessor:
    """Layer 1: Tactical Analysis (Data Volley Integration)"""
    
    def __init__(self):
        self.tactical_analyzer = TacticalAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    async def process_tactical_layer(self, request: AnalysisRequest) -> Dict:
        """Process tactical layer analysis"""
        
        self.logger.info(f"[Layer1] Starting tactical analysis for {request.video_path}")
        
        try:
            # If Data Volley file provided, parse it directly
            if request.dvw_file_path and Path(request.dvw_file_path).exists():
                tactical_analysis = analyze_tactical_match(request.dvw_file_path, request.video_path)
            else:
                # Generate tactical analysis from video (placeholder)
                tactical_analysis = await self.generate_tactical_from_video(request.video_path)
            
            # Enhance with tournament context
            tactical_analysis['tournament_context'] = {
                'level': request.tournament_context,
                'analysis_level': request.analysis_level,
                'benchmarks_used': 'FIVB Level II + Open Spike Kinematics'
            }
            
            self.logger.info(f"[Layer1] Tactical analysis completed: {len(tactical_analysis.get('rally_analysis', []))} rallies")
            
            return tactical_analysis
            
        except Exception as e:
            self.logger.error(f"[Layer1] Tactical analysis failed: {e}")
            return {'error': str(e), 'status': 'failed'}
    
    async def generate_tactical_from_video(self, video_path: str) -> Dict:
        """Generate tactical analysis from video when .dvw file not available"""
        
        # This would use computer vision to detect formations, plays, etc.
        # For now, return placeholder data
        
        return {
            'match_summary': {
                'total_actions': 0,
                'rally_count': 0,
                'note': 'Tactical analysis requires Data Volley (.dvw) file for full analysis'
            },
            'rally_analysis': [],
            'tactical_patterns': {},
            'status': 'video_only_analysis'
        }

class Layer2BiomechanicalProcessor:
    """Layer 2: Biomechanical Analysis (SAM2 + ViTPose)"""
    
    def __init__(self):
        self.action_detector = VolleyballMultiTracker()  # Reuse multi-tracker for detection
        self.logger = logging.getLogger(__name__)
    
    async def process_biomechanical_layer(self, request: AnalysisRequest, tactical_data: Optional[Dict] = None) -> Dict:
        """Process biomechanical layer analysis"""
        
        self.logger.info(f"[Layer2] Starting biomechanical analysis for {request.video_path}")
        
        try:
            # Step 1: Temporal action localization
            actions, action_clips = await self.localize_actions(request.video_path)
            
            # Step 2: Multi-player tracking (if needed)
            player_tracks = await self.track_players(request.video_path)
            
            # Step 3: Biomechanical analysis for each action
            biomechanical_results = await self.analyze_biomechanics(actions, request)
            
            # Step 4: Elite benchmark comparison
            elite_comparisons = await self.compare_to_elite_standards(biomechanical_results, request)
            
            # Step 5: Position detection
            positions = await self.detect_player_positions(biomechanical_results)
            
            biomechanical_analysis = {
                'actions_detected': len(actions),
                'players_tracked': len(player_tracks),
                'biomechanical_results': biomechanical_results,
                'elite_comparisons': elite_comparisons,
                'detected_positions': positions,
                'action_clips': action_clips,
                'quality_metrics': self.calculate_biomechanical_quality(biomechanical_results)
            }
            
            self.logger.info(f"[Layer2] Biomechanical analysis completed: {len(biomechanical_results)} actions analyzed")
            
            return biomechanical_analysis
            
        except Exception as e:
            self.logger.error(f"[Layer2] Biomechanical analysis failed: {e}")
            return {'error': str(e), 'status': 'failed'}
    
    async def localize_actions(self, video_path: str) -> Tuple[List[ActionSegment], List[str]]:
        """Localize volleyball actions in video"""
        
        # Use temporal action localizer
        actions, clips = detect_volleyball_actions(video_path)
        
        self.logger.info(f"[Layer2] Localized {len(actions)} volleyball actions")
        
        return actions, clips
    
    async def track_players(self, video_path: str) -> List[PlayerTrack]:
        """Track multiple players in video"""
        
        # This would process the entire video and return player tracks
        # For now, return placeholder
        
        return []
    
    async def analyze_biomechanics(self, actions: List[ActionSegment], request: AnalysisRequest) -> List[Dict]:
        """Analyze biomechanics for each detected action"""
        
        results = []
        
        for i, action in enumerate(actions):
            try:
                # Extract pose for this action segment
                biomechanical_data = await self.extract_pose_biomechanics(action, request.video_path)
                
                if biomechanical_data:
                    results.append({
                        'action_id': i,
                        'timestamp': action.start_time,
                        'action_type': action.action_type,
                        'confidence': action.confidence,
                        'biomechanical_data': biomechanical_data
                    })
                    
            except Exception as e:
                self.logger.warning(f"[Layer2] Biomechanical analysis failed for action {i}: {e}")
                continue
        
        return results
    
    async def extract_pose_biomechanics(self, action: ActionSegment, video_path: str) -> Optional[Dict]:
        """Extract pose and biomechanical data for action segment"""
        
        # This would use SAM2 + ViTPose to extract joint coordinates
        # For now, return simulated data
        
        return {
            'joint_angles': {
                'elbow_flexion': 143.2,
                'torso_extension': 142.1,
                'knee_flexion': 118.7,
                'shoulder_rotation': 135.4
            },
            'joint_velocities': {
                'elbow_extension': 8.2,
                'shoulder_rotation': 12.1
            },
            'temporal_features': {
                'approach_duration': 1.1,
                'arm_swing_duration': 0.28
            },
            'spatial_features': {
                'jump_height': 0.65,
                'approach_angle': 43.2
            }
        }
    
    async def compare_to_elite_standards(self, biomechanical_results: List[Dict], request: AnalysisRequest) -> Dict:
        """Compare biomechanical results to elite standards"""
        
        elite_comparisons = {}
        
        for result in biomechanical_results:
            action_type = result['action_type']
            biomechanical_data = result['biomechanical_data']
            
            # Get elite benchmarks
            comparison = {}
            for joint, value in biomechanical_data.get('joint_angles', {}).items():
                benchmark = get_elite_benchmark(action_type, joint, 'general')  # Could use detected position
                if benchmark:
                    deviation = value - benchmark['mean']
                    assessment, severity = self.fivb_data.generate_deviation_assessment(value, benchmark)
                    
                    comparison[joint] = {
                        'measured': value,
                        'elite_mean': benchmark['mean'],
                        'elite_std': benchmark['std'],
                        'deviation': deviation,
                        'assessment': assessment,
                        'severity': severity
                    }
            
            elite_comparisons[action_type] = comparison
        
        return elite_comparisons
    
    async def detect_player_positions(self, biomechanical_results: List[Dict]) -> Dict:
        """Detect player positions from movement patterns"""
        
        positions = {}
        
        for result in biomechanical_results:
            # Use movement patterns to infer position
            position = detect_position_from_movement(result['biomechanical_data'])
            positions[result['action_id']] = position
        
        return positions
    
    def calculate_biomechanical_quality(self, results: List[Dict]) -> Dict:
        """Calculate quality metrics for biomechanical analysis"""
        
        if not results:
            return {'overall_quality': 0.0, 'confidence_score': 0.0}
        
        total_actions = len(results)
        high_confidence_actions = sum(1 for r in results if r.get('confidence', 0) > 0.7)
        
        return {
            'overall_quality': high_confidence_actions / total_actions,
            'confidence_score': np.mean([r.get('confidence', 0) for r in results]),
            'actions_analyzed': total_actions
        }

class Layer3LLMProcessor:
    """Layer 3: LLM Analysis and Insights Generation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.training_data_generator = None  # Will be initialized when needed
    
    async def process_llm_layer(self, request: AnalysisRequest, tactical_data: Dict, biomechanical_data: Dict) -> Dict:
        """Process LLM layer for insights generation"""
        
        self.logger.info("[Layer3] Starting LLM analysis and insights generation")
        
        try:
            # Step 1: Integrate tactical and biomechanical data
            integrated_data = await self.integrate_layers(tactical_data, biomechanical_data)
            
            # Step 2: Generate contextual insights
            insights = await self.generate_contextual_insights(integrated_data, request)
            
            # Step 3: Create training recommendations
            recommendations = await self.generate_training_recommendations(integrated_data, request)
            
            # Step 4: Assess competition readiness
            readiness = await self.assess_competition_readiness(integrated_data, request)
            
            # Step 5: Generate personalized coaching feedback
            coaching_feedback = await self.generate_coaching_feedback(integrated_data, request)
            
            llm_analysis = {
                'integrated_assessment': integrated_data,
                'contextual_insights': insights,
                'training_recommendations': recommendations,
                'competition_readiness': readiness,
                'coaching_feedback': coaching_feedback,
                'llm_quality_score': self.calculate_llm_quality_score(insights, recommendations)
            }
            
            self.logger.info("[Layer3] LLM analysis completed successfully")
            
            return llm_analysis
            
        except Exception as e:
            self.logger.error(f"[Layer3] LLM analysis failed: {e}")
            return {'error': str(e), 'status': 'failed'}
    
    async def integrate_layers(self, tactical_data: Dict, biomechanical_data: Dict) -> Dict:
        """Integrate tactical and biomechanical data for comprehensive analysis"""
        
        # Use the tactical integration function
        integrated_data = integrate_tactical_biomechanical(tactical_data, biomechanical_data)
        
        # Add layer-specific metadata
        integrated_data['integration_metadata'] = {
            'tactical_layer_quality': tactical_data.get('quality_metrics', {}).get('overall_quality', 0),
            'biomechanical_layer_quality': biomechanical_data.get('quality_metrics', {}).get('overall_quality', 0),
            'integration_timestamp': datetime.now().isoformat(),
            'integration_method': 'contextual_alignment'
        }
        
        return integrated_data
    
    async def generate_contextual_insights(self, integrated_data: Dict, request: AnalysisRequest) -> List[Dict]:
        """Generate contextual insights combining tactical and biomechanical data"""
        
        insights = []
        
        # Analyze integrated insights
        for insight in integrated_data.get('integrated_insights', []):
            contextual_insight = {
                'timestamp': insight.get('timestamp'),
                'tactical_context': insight.get('tactical_context', {}),
                'biomechanical_deviations': insight.get('biomechanical_analysis', {}).get('deviations', {}),
                'contextual_assessment': self.generate_contextual_assessment(insight),
                'coaching_priority': self.assess_coaching_priority(insight),
                'actionable_recommendation': self.generate_actionable_recommendation(insight)
            }
            
            insights.append(contextual_insight)
        
        return insights
    
    def generate_contextual_assessment(self, insight: Dict) -> str:
        """Generate contextual assessment combining tactical and biomechanical data"""
        
        tactical_context = insight.get('tactical_context', {})
        biomechanical_data = insight.get('biomechanical_analysis', {})
        
        # Generate assessment based on both layers
        set_tempo = tactical_context.get('set_tempo', 'unknown')
        attack_zone = tactical_context.get('attack_zone', 0)
        deviations = biomechanical_data.get('deviations', {})
        
        assessment_parts = []
        
        if set_tempo == 'first_tempo' and deviations:
            assessment_parts.append("Fast tempo set with biomechanical deviations detected")
        
        if attack_zone in [1, 2, 3] and deviations.get('approach_angle', 0) > 5:
            assessment_parts.append("Front court attack with suboptimal approach angle")
        
        if not assessment_parts:
            assessment_parts.append("Technique shows good integration of tactical and biomechanical elements")
        
        return "; ".join(assessment_parts)
    
    def assess_coaching_priority(self, insight: Dict) -> str:
        """Assess coaching priority for this insight"""
        
        deviations = insight.get('biomechanical_analysis', {}).get('deviations', {})
        tactical_context = insight.get('tactical_context', {})
        
        # Higher priority for significant deviations in important tactical contexts
        max_deviation = max([abs(dev) for dev in deviations.values()], default=0)
        
        if max_deviation > 15 and tactical_context.get('set_tempo') == 'first_tempo':
            return 'high'
        elif max_deviation > 10:
            return 'medium'
        else:
            return 'low'
    
    def generate_actionable_recommendation(self, insight: Dict) -> str:
        """Generate actionable recommendation based on integrated analysis"""
        
        # This would use a trained LLM in production
        # For now, return structured recommendation
        
        tactical_context = insight.get('tactical_context', {})
        deviations = insight.get('biomechanical_analysis', {}).get('deviations', {})
        
        recommendations = []
        
        if tactical_context.get('set_tempo') == 'first_tempo' and 'approach_angle' in deviations:
            recommendations.append("On fast tempo sets, focus on earlier approach initiation to achieve optimal angle")
        
        if tactical_context.get('reception_quality', 3) < 2 and 'torso_extension' in deviations:
            recommendations.append("Poor reception quality may be affecting approach mechanics - work on reception fundamentals")
        
        if not recommendations:
            recommendations.append("Continue current training focus while monitoring progress")
        
        return " ".join(recommendations)
    
    async def generate_training_recommendations(self, integrated_data: Dict, request: AnalysisRequest) -> List[Dict]:
        """Generate personalized training recommendations"""
        
        recommendations = []
        
        # Analyze patterns in integrated data
        tactical_patterns = integrated_data.get('tactical_context', {}).get('tactical_patterns', {})
        biomechanical_issues = self.identify_biomechanical_issues(integrated_data)
        
        # Generate position-specific recommendations
        if request.athlete_id:
            position = self.infer_player_position(integrated_data)
            position_recommendations = self.generate_position_recommendations(position, tactical_patterns, biomechanical_issues)
            recommendations.extend(position_recommendations)
        
        # Generate technique-specific recommendations
        technique_recommendations = self.generate_technique_recommendations(tactical_patterns, biomechanical_issues)
        recommendations.extend(technique_recommendations)
        
        # Add 8-week training program if requested
        if request.include_training_program:
            training_program = self.generate_8_week_program(recommendations, request.analysis_level)
            recommendations.append(training_program)
        
        return recommendations
    
    def identify_biomechanical_issues(self, integrated_data: Dict) -> List[Dict]:
        """Identify consistent biomechanical issues across actions"""
        
        issues = []
        insights = integrated_data.get('integrated_insights', [])
        
        # Aggregate deviations across all insights
        deviation_summary = {}
        
        for insight in insights:
            deviations = insight.get('biomechanical_analysis', {}).get('deviations', {})
            for joint, deviation in deviations.items():
                if joint not in deviation_summary:
                    deviation_summary[joint] = []
                deviation_summary[joint].append(deviation)
        
        # Identify consistent issues
        for joint, deviations in deviation_summary.items():
            if len(deviations) >= 3:  # At least 3 occurrences
                avg_deviation = np.mean([abs(d) for d in deviations])
                consistency = np.std([abs(d) for d in deviations])
                
                if avg_deviation > 10 and consistency < 5:  # Significant and consistent
                    issues.append({
                        'joint': joint,
                        'average_deviation': avg_deviation,
                        'consistency': consistency,
                        'frequency': len(deviations),
                        'priority': 'high' if avg_deviation > 15 else 'medium'
                    })
        
        return issues
    
    def generate_position_recommendations(self, position: str, tactical_patterns: Dict, biomechanical_issues: List[Dict]) -> List[Dict]:
        """Generate position-specific training recommendations"""
        
        recommendations = []
        
        # Position-specific focus areas
        position_focus = {
            'middle': ['block_timing', 'quick_attack', 'transition_footwork'],
            'opposite': ['back_row_attack', 'serve_consistency', 'block_reading'],
            'outside': ['reception', 'approach_timing', 'cross_court_attacks'],
            'libero': ['reception', 'defensive_positioning', 'ball_control'],
            'setter': ['setting_consistency', 'decision_making', 'defensive_transition']
        }
        
        focus_areas = position_focus.get(position, ['general_skills'])
        
        for area in focus_areas:
            recommendation = {
                'category': 'position_specific',
                'position': position,
                'focus_area': area,
                'priority': 'high',
                'description': f"Focus on {area} skills specific to {position} position",
                'drills': self.get_position_drills(position, area),
                'metrics': self.get_position_metrics(position, area)
            }
            
            # Integrate biomechanical issues
            relevant_issues = [issue for issue in biomechanical_issues if self.is_relevant_to_position(issue['joint'], position)]
            if relevant_issues:
                recommendation['biomechanical_focus'] = relevant_issues
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def generate_technique_recommendations(self, tactical_patterns: Dict, biomechanical_issues: List[Dict]) -> List[Dict]:
        """Generate technique-specific recommendations"""
        
        recommendations = []
        
        # Analyze tactical patterns for technique recommendations
        serve_patterns = tactical_patterns.get('serve', {})
        attack_patterns = tactical_patterns.get('attack', {})
        
        # Serve recommendations
        if serve_patterns.get('quality_distribution', {}).get(1, 0) > 0.3:  # >30% poor quality
            recommendations.append({
                'category': 'technique',
                'technique': 'serve',
                'priority': 'high',
                'description': 'High percentage of poor serves - focus on consistency',
                'focus_areas': ['toss_consistency', 'contact_timing', 'follow_through'],
                'drills': ['Target serving', 'Toss consistency', 'Pressure serving']
            })
        
        # Attack recommendations
        if attack_patterns.get('tempo_distribution', {}).get('high_ball', 0) > 0.6:  # >60% high balls
            recommendations.append({
                'category': 'technique',
                'technique': 'attack',
                'priority': 'medium',
                'description': 'Over-reliance on high ball attacks - incorporate faster tempos',
                'focus_areas': ['approach_timing', 'quick_attack', 'tempo_variation'],
                'drills': ['First tempo attacks', 'Approach timing', 'Tempo variation']
            })
        
        return recommendations
    
    def generate_8_week_program(self, recommendations: List[Dict], analysis_level: str) -> Dict:
        """Generate 8-week elite training program"""
        
        # This would be much more sophisticated in production
        # For now, return structured program template
        
        program = {
            'category': 'training_program',
            'type': '8_week_elite_program',
            'duration_weeks': 8,
            'analysis_level': analysis_level,
            'structure': {
                'weeks_1_2': {'focus': 'assessment_and_fundamentals', 'intensity': 'moderate'},
                'weeks_3_4': {'focus': 'technique_refinement', 'intensity': 'high'},
                'weeks_5_6': {'focus': 'integration_and_speed', 'intensity': 'very_high'},
                'weeks_7_8': {'focus': 'competition_preparation', 'intensity': 'peak'}
            },
            'weekly_schedule': {
                'monday': 'Technical skills + Strength',
                'tuesday': 'Tactical work + Conditioning',
                'wednesday': 'Recovery + Video analysis',
                'thursday': 'Technical skills + Power',
                'friday': 'Tactical scrimmage + Mental training',
                'saturday': 'Competition simulation',
                'sunday': 'Recovery + Planning'
            },
            'key_performance_indicators': [
                'Biomechanical deviation reduction',
                'Tactical execution percentage',
                'Consistency metrics',
                'Competition readiness score'
            ],
            'progression_criteria': {
                'advancement_threshold': '80% completion of weekly goals',
                'adjustment_triggers': ['Performance plateaus', 'Injury concerns', 'Competition schedule changes']
            }
        }
        
        # Add specific recommendations to program
        high_priority_recs = [rec for rec in recommendations if rec.get('priority') == 'high']
        if high_priority_recs:
            program['priority_focus_areas'] = high_priority_recs
        
        return program
    
    async def assess_competition_readiness(self, integrated_data: Dict, request: AnalysisRequest) -> Dict:
        """Assess athlete's readiness for competition"""
        
        # Calculate readiness based on multiple factors
        tactical_readiness = self.calculate_tactical_readiness(integrated_data)
        biomechanical_readiness = self.calculate_biomechanical_readiness(integrated_data)
        consistency_score = self.calculate_consistency_score(integrated_data)
        
        # Overall readiness score
        overall_readiness = (tactical_readiness + biomechanical_readiness + consistency_score) / 3
        
        return {
            'overall_readiness': overall_readiness,
            'tactical_readiness': tactical_readiness,
            'biomechanical_readiness': biomechanical_readiness,
            'consistency_score': consistency_score,
            'readiness_level': self.categorize_readiness(overall_readiness),
            'recommendations': self.generate_readiness_recommendations(overall_readiness, request.tournament_context)
        }
    
    def calculate_tactical_readiness(self, integrated_data: Dict) -> float:
        """Calculate tactical readiness score"""
        
        tactical_patterns = integrated_data.get('tactical_context', {}).get('tactical_patterns', {})
        
        # Score based on tactical pattern quality
        serve_quality = 1.0 - tactical_patterns.get('serve', {}).get('quality_distribution', {}).get(1, 0)  # Lower poor quality = higher readiness
        attack_variety = len(tactical_patterns.get('attack', {}).get('tempo_distribution', {})) / 3.0  # More tempo variety = higher readiness
        
        return min(1.0, (serve_quality + attack_variety) / 2)
    
    def calculate_biomechanical_readiness(self, integrated_data: Dict) -> float:
        """Calculate biomechanical readiness score"""
        
        # Score based on biomechanical consistency and elite alignment
        issues = self.identify_biomechanical_issues(integrated_data)
        
        if not issues:
            return 1.0  # No issues = full readiness
        
        # Score based on severity and frequency of issues
        severity_scores = [1.0 - (issue['average_deviation'] / 30) for issue in issues]  # Normalize severity
        avg_severity = np.mean(severity_scores)
        
        return max(0.0, avg_severity)
    
    def calculate_consistency_score(self, integrated_data: Dict) -> float:
        """Calculate consistency score across actions"""
        
        insights = integrated_data.get('integrated_insights', [])
        
        if not insights:
            return 0.5  # Neutral score if no data
        
        # Score based on consistency of assessments
        assessments = [insight.get('coaching_priority', 'low') for insight in insights]
        high_priority_ratio = assessments.count('high') / len(assessments)
        
        return 1.0 - high_priority_ratio  # Lower high priority ratio = higher consistency
    
    def categorize_readiness(self, score: float) -> str:
        """Categorize readiness level"""
        
        if score >= 0.85:
            return 'competition_ready'
        elif score >= 0.70:
            return 'near_ready'
        elif score >= 0.55:
            return 'development_needed'
        else:
            return 'significant_work_needed'
    
    def generate_readiness_recommendations(self, readiness: float, tournament_context: str) -> List[str]:
        """Generate recommendations based on readiness level"""
        
        level = self.categorize_readiness(readiness)
        
        recommendations = {
            'competition_ready': ['Maintain current training regimen', 'Focus on competition preparation', 'Monitor for any changes'],
            'near_ready': ['Address identified technical issues', 'Increase competition-specific training', 'Fine-tune tactical execution'],
            'development_needed': ['Focus on fundamental skill development', 'Address biomechanical issues', 'Build consistency through repetition'],
            'significant_work_needed': ['Comprehensive skill development program', 'Address multiple technical areas', 'Extended preparation timeline']
        }
        
        return recommendations.get(level, ['Continue skill development'])
    
    async def generate_coaching_feedback(self, integrated_data: Dict, request: AnalysisRequest) -> str:
        """Generate comprehensive coaching feedback"""
        
        # This would use a trained LLM in production
        # For now, return structured feedback
        
        tactical_summary = self.summarize_tactical_performance(integrated_data)
        biomechanical_summary = self.summarize_biomechanical_performance(integrated_data)
        readiness_level = self.categorize_readiness(integrated_data.get('competition_readiness', {}).get('overall_readiness', 0.5))
        
        feedback_parts = [
            f"Tactical Performance: {tactical_summary}",
            f"Biomechanical Analysis: {biomechanical_summary}",
            f"Competition Readiness: {readiness_level.replace('_', ' ').title()}",
            "Recommendations: Follow the generated training program focusing on identified priority areas."
        ]
        
        return "\n".join(feedback_parts)
    
    def summarize_tactical_performance(self, integrated_data: Dict) -> str:
        """Summarize tactical performance"""
        
        tactical_patterns = integrated_data.get('tactical_context', {}).get('tactical_patterns', {})
        
        serve_quality = tactical_patterns.get('serve', {}).get('quality_distribution', {})
        attack_tempo = tactical_patterns.get('attack', {}).get('tempo_distribution', {})
        
        serve_summary = f"Serve quality shows {serve_quality.get(1, 0)*100:.0f}% poor execution" if serve_quality.get(1, 0) > 0.2 else "Serve quality is consistent"
        attack_summary = f"Attack variety includes {len(attack_tempo)} different tempos" if attack_tempo else "Attack patterns need development"
        
        return f"{serve_summary}. {attack_summary}."
    
    def summarize_biomechanical_performance(self, integrated_data: Dict) -> str:
        """Summarize biomechanical performance"""
        
        issues = self.identify_biomechanical_issues(integrated_data)
        
        if not issues:
            return "Biomechanics align well with elite standards"
        
        high_priority_issues = [issue for issue in issues if issue['priority'] == 'high']
        
        if high_priority_issues:
            return f"{len(high_priority_issues)} high-priority biomechanical issues identified requiring immediate attention"
        else:
            return f"{len(issues)} biomechanical areas identified for improvement"
    
    def calculate_llm_quality_score(self, insights: List[Dict], recommendations: List[Dict]) -> float:
        """Calculate quality score for LLM analysis"""
        
        # Score based on insight quality and recommendation relevance
        insight_quality = len([i for i in insights if i.get('coaching_priority') in ['high', 'medium']]) / max(len(insights), 1)
        recommendation_count = len(recommendations)
        
        # Balance between insight depth and actionable recommendations
        quality_score = (insight_quality * 0.6) + (min(recommendation_count / 5, 1.0) * 0.4)
        
        return quality_score

class IntegratedAnalysisOrchestrator:
    """Main orchestrator for three-layer analysis"""
    
    def __init__(self):
        self.layer1_processor = Layer1TacticalProcessor()
        self.layer2_processor = Layer2BiomechanicalProcessor()
        self.layer3_processor = Layer3LLMProcessor()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
    
    async def process_comprehensive_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """Process comprehensive three-layer analysis"""
        
        start_time = datetime.now()
        request_id = f"analysis_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"[Orchestrator] Starting comprehensive analysis: {request_id}")
        
        result = AnalysisResult(
            request_id=request_id,
            timestamp=start_time,
            status='processing'
        )
        
        try:
            # Layer 1: Tactical Analysis
            self.logger.info("[Orchestrator] Processing Layer 1: Tactical Analysis")
            tactical_data = await self.layer1_processor.process_tactical_layer(request)
            result.layer_1_tactical = tactical_data
            
            if tactical_data.get('status') == 'failed':
                raise Exception("Tactical analysis failed")
            
            # Layer 2: Biomechanical Analysis
            self.logger.info("[Orchestrator] Processing Layer 2: Biomechanical Analysis")
            biomechanical_data = await self.layer2_processor.process_biomechanical_layer(request, tactical_data)
            result.layer_2_biomechanical = biomechanical_data
            
            if biomechanical_data.get('status') == 'failed':
                raise Exception("Biomechanical analysis failed")
            
            # Layer 3: LLM Analysis
            self.logger.info("[Orchestrator] Processing Layer 3: LLM Analysis")
            llm_data = await self.layer3_processor.process_llm_layer(request, tactical_data, biomechanical_data)
            result.layer_3_llm_insights = llm_data
            
            if llm_data.get('status') == 'failed':
                raise Exception("LLM analysis failed")
            
            # Final integration
            self.logger.info("[Orchestrator] Finalizing comprehensive analysis")
            result.integrated_assessment = llm_data.get('integrated_assessment', {})
            result.training_recommendations = llm_data.get('training_recommendations', [])
            result.competition_readiness = llm_data.get('competition_readiness', {})
            result.quality_score = self.calculate_overall_quality_score(result)
            
            # Calculate processing time
            result.processing_time = (datetime.now() - start_time).total_seconds()
            result.status = 'completed'
            
            self.logger.info(f"[Orchestrator] Analysis completed successfully: {request_id} ({result.processing_time:.1f}s)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Orchestrator] Analysis failed: {e}")
            result.status = 'failed'
            result.processing_time = (datetime.now() - start_time).total_seconds()
            return result
    
    def calculate_overall_quality_score(self, result: AnalysisResult) -> float:
        """Calculate overall quality score for the analysis"""
        
        # Weight different layers
        tactical_quality = result.layer_1_tactical.get('quality_metrics', {}).get('overall_quality', 0) if result.layer_1_tactical else 0
        biomechanical_quality = result.layer_2_biomechanical.get('quality_metrics', {}).get('overall_quality', 0) if result.layer_2_biomechanical else 0
        llm_quality = result.layer_3_llm_insights.get('llm_quality_score', 0) if result.layer_3_llm_insights else 0
        
        # Weighted average (tactical and biomechanical are more objective)
        overall_score = (
            0.35 * tactical_quality +
            0.35 * biomechanical_quality +
            0.30 * llm_quality
        )
        
        return min(overall_score, 1.0)

# Global orchestrator instance
analysis_orchestrator = IntegratedAnalysisOrchestrator()

async def process_volleyball_analysis(request: AnalysisRequest) -> AnalysisResult:
    """Main entry point for comprehensive volleyball analysis"""
    return await analysis_orchestrator.process_comprehensive_analysis(request)

def create_analysis_request(
    video_path: str,
    dvw_file_path: Optional[str] = None,
    athlete_id: Optional[str] = None,
    tournament_context: str = "training",
    analysis_level: str = "elite"
) -> AnalysisRequest:
    """Create analysis request with validation"""
    
    # Validate inputs
    if not Path(video_path).exists():
        raise ValueError(f"Video file not found: {video_path}")
    
    if dvw_file_path and not Path(dvw_file_path).exists():
        logging.warning(f"Data Volley file not found: {dvw_file_path}. Tactical analysis will be limited.")
        dvw_file_path = None
    
    return AnalysisRequest(
        video_path=video_path,
        dvw_file_path=dvw_file_path,
        athlete_id=athlete_id,
        tournament_context=tournament_context,
        analysis_level=analysis_level
    )